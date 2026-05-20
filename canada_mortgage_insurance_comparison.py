# Copyright (c) 2023-2026 Samuel Plamondon

# NOTE: this calculator was created in 2023 based on mortgage insurance rules
# in place at that time. It has not been updated since then. It is possible
# that rules, rates, etc. have changed since then, in which case the
# calculator may no longer be accurate.

# Imports:

import numpy as np

# Functions taken from "numpy_financial" package
# (https://github.com/numpy/numpy-financial), as online compilers did not
# support this package as of 2023:

_when_to_num = {'end': 0, 'begin': 1,
                'e': 0, 'b': 1,
                0: 0, 1: 1,
                'beginning': 1,
                'start': 1,
                'finish': 0}

def _convert_when(when):
    # Test to see if when has already been converted to ndarray
    # This will happen if one function calls another, for example ppmt
    if isinstance(when, np.ndarray):
        return when
    try:
        return _when_to_num[when]
    except (KeyError, TypeError):
        return [_when_to_num[x] for x in when]

def pmt(rate, nper, pv, fv=0, when='end'):
    """
    Compute the payment against loan principal plus interest.

    Given:
     * a present value, `pv` (e.g., an amount borrowed)
     * a future value, `fv` (e.g., 0)
     * an interest `rate` compounded once per period, of which
       there are
     * `nper` total
     * and (optional) specification of whether payment is made
       at the beginning (`when` = {'begin', 1}) or the end
       (`when` = {'end', 0}) of each period

    Return:
       the (fixed) periodic payment.

    Parameters
    ----------
    rate : array_like
        Rate of interest (per period)
    nper : array_like
        Number of compounding periods
    pv : array_like
        Present value
    fv : array_like,  optional
        Future value (default = 0)
    when : {{'begin', 1}, {'end', 0}}, {string, int}
        When payments are due ('begin' (1) or 'end' (0))

    Returns
    -------
    out : ndarray
        Payment against loan plus interest.  If all input is scalar, returns a
        scalar float.  If any input is array_like, returns payment for each
        input element. If multiple inputs are array_like, they all must have
        the same shape.

    Notes
    -----
    The payment is computed by solving the equation::

     fv +
     pv*(1 + rate)**nper +
     pmt*(1 + rate*when)/rate*((1 + rate)**nper - 1) == 0

    or, when ``rate == 0``::

      fv + pv + pmt * nper == 0

    for ``pmt``.

    Note that computing a monthly mortgage payment is only
    one use for this function.  For example, pmt returns the
    periodic deposit one must make to achieve a specified
    future balance given an initial deposit, a fixed,
    periodically compounded interest rate, and the total
    number of periods.

    References
    ----------
    .. [WRW] Wheeler, D. A., E. Rathke, and R. Weir (Eds.) (2009, May).
       Open Document Format for Office Applications (OpenDocument)v1.2,
       Part 2: Recalculated Formula (OpenFormula) Format - Annotated Version,
       Pre-Draft 12. Organization for the Advancement of Structured Information
       Standards (OASIS). Billerica, MA, USA. [ODT Document].
       Available:
       http://www.oasis-open.org/committees/documents.php
       ?wg_abbrev=office-formulaOpenDocument-formula-20090508.odt

    Examples
    --------
    >>> import numpy_financial as npf

    What is the monthly payment needed to pay off a $200,000 loan in 15
    years at an annual interest rate of 7.5%?

    >>> npf.pmt(0.075/12, 12*15, 200000)
    -1854.0247200054619

    In order to pay-off (i.e., have a future-value of 0) the $200,000 obtained
    today, a monthly payment of $1,854.02 would be required.  Note that this
    example illustrates usage of `fv` having a default value of 0.

    """
    when = _convert_when(when)
    (rate, nper, pv, fv, when) = map(np.array, [rate, nper, pv, fv, when])
    temp = (1 + rate)**nper
    mask = (rate == 0)
    masked_rate = np.where(mask, 1, rate)
    fact = np.where(mask != 0, nper,
                    (1 + masked_rate*when)*(temp - 1)/masked_rate)
    return -(fv + pv*temp) / fact

# Functions:

def mortgage_payment(r, l, a):
    
    """
    r: float, annual interest rate, in percent
    l: float, total loan amount, in dollars
    a: int, amortization in years
    returns: p (float), the monthly mortgage payment in dollars
    """
    
    biann_r = 1 + r/200
    month_r = biann_r**(1/6)
    p = -pmt(month_r - 1, a*12, l)
    
    return p

def princ_calc(y, l, r, p):
    
    """
    y: int, the term period in years
    l: float, loan amount, in dollars
    r: float, annual interest rate, in percent
    p: float, the monthly mortgage payment in dollars
    returns: princ_paid (float), the amount of principal paid off over the
        life of the contract, in dollars
    """
    
    biann_r = 1 + r/200
    month_r = biann_r**(1/6)
    months_remaining = y*12
    l_remaining = l
    princ_paid = 0
    
    while months_remaining > 0:
        
        princ_paid_month = p - l_remaining*(month_r - 1)
        princ_paid += princ_paid_month
        l_remaining -= princ_paid_month
        months_remaining -= 1
    
    return princ_paid

def cmhc_insurance(l, d, prov):
    
    """
    l: float, loan amount, in dollars
    d: float, down payment amount, in dollars
    prov: string, province of purchase
    returns:
        - ins (float), the CMHC mortgage insurance cost over the initial term,
            in dollars
        - ins_tax (float), the tax paid on the CMHC mortgage insurance, in
            dollars
    """
    
    ltv = l/(l + d)
    
    if ltv <= 0.65:
        ins = 0.006*l
    elif ltv <= 0.75:
        ins = 0.017*l
    else:
        ins = 0.024*l
    
    ins_tax = 0
    prov_l = prov.lower()
    
    if prov_l == 'quebec':
        ins_tax = ins*0.09975
    elif prov_l == 'ontario':
        ins_tax = ins*0.13
    elif prov_l == 'saskatchewan':
        ins_tax = ins*0.06
    
    return ins, ins_tax

def cost_over_term(y, l, tot, insured, a, is_init):
    
    """
    y: int, the term period in years
    l: float, loan amount, in dollars
    tot: float, purchase price, in dollars
    ins_purchased: Boolean, True if mortgage insurance is being purchased with
        this loan contract
    insured: Boolean, True if the mortgage loan is insured
    a: int, amortization in years
    is_init: Boolean, True if this is the initial term
    returns:
        - term_cost (float), the total mortgage cost over the life of the
            contract, in dollars
        - princ_paid (float), the amount of principal paid off over the life
            of the contract, in dollars
    """
    
    if insured:
        
        if is_init:
            r = r_ins_init
        else:
            r = r_ins
    
    else:
    
        if is_init:
            
            r = r_un_init
        
        else:
            
            ltv = l/tot
            
            if ltv <= 0.65:
                r = r_un_65
            elif ltv <= 0.70:
                r = r_un_70
            elif ltv <= 0.75:
                r = r_un_75
            else:
                r = r_un_80
    
    p = mortgage_payment(r, l, a)
    term_cost = y*12*p
    princ_paid = princ_calc(y, l, r, p)
    
    return term_cost, princ_paid

def cost_over_mortgage(y, l, tot, insured, a):
    
    """
    y: int, the term period in years
    l: float, loan amount, in dollars
    tot: float, purchase price, in dollars
    insured: Boolean, True if mortgage insurance is purchased when the loan is
        first taken
    a: int, amortization in years
    returns: tot_cost (float), the total mortgage cost over all terms, in
        dollars
    """
    
    a_remaining = a
    l_remaining = l
    tot_cost = 0
    
    if insured:
        
        ins, ins_tax = cmhc_insurance(l, (tot - l), prov)
        l_remaining += ins
        tot_cost += ins_tax
    
    term_cost, princ_paid = cost_over_term(y, l_remaining, tot, insured,
                                           a_remaining, True)
    tot_cost += term_cost
    a_remaining -= y
    l_remaining -= princ_paid
    
    while a_remaining >= y:
        
        term_cost, princ_paid = cost_over_term(y, l_remaining, tot, insured,
                                               a_remaining, False)
        tot_cost += term_cost
        a_remaining -= y
        l_remaining -= princ_paid
    
    tot_cost += l_remaining
    
    return tot_cost

# Main:
    
tot = float(input("Please enter the purchase price ($): "))
d = float(input("\nPlease enter the down payment ($): "))
a = int(input("\nPlease enter the initial amortization period, in years: "))

if tot >= 1000000:
    
    print("\nThe house is not eligible for mortgage insurance since it costs",
          "$1 million or more.")

elif d/tot < 0.2:
    
    print("\nSince your down payment is less than 20%, you will need to get",
          "mortgage insurance.")

elif a > 25:
    
    print("\nInsured mortgages cannot have amortizations longer than 25",
          "years.")

else:
    
    l = tot - d
    
    prov = input("\nProvince where property is located (omit accents): ")
    
    r_ins_init = float(input("\nInitial interest rate if insured (%): "))
    r_un_init = float(input("\nInitial interest rate if uninsured (%): "))
    r_ins = float(input("\nEstimated future interest rate if insured (%): "))
    
    print("\nEstimated future interest rate if uninsured...")
    r_un_80 = float(input("...75-80% LTV (%): "))
    r_un_75 = float(input("...70-75% LTV (%): "))
    r_un_70 = float(input("...65-70% LTV (%): "))
    r_un_65 = float(input("...0-65% LTV (%): "))
    
    y = int(input("\nPlease enter the term period, in years: "))
    
    tot_cost_ins = cost_over_mortgage(y, l, tot, True, a)
    
    print("\nThe total cost of the insured mortgage is: $"
          + str(round(tot_cost_ins, 2)))
    
    tot_cost_un = cost_over_mortgage(y, l, tot, False, a)
    
    print("\nThe total cost of the uninsured mortgage is: $"
          + str(round(tot_cost_un, 2)))
    
    if tot_cost_ins < tot_cost_un:
        print("\nThe insured mortgage is less expensive.")
    elif tot_cost_un < tot_cost_ins:
        print("\nThe uninsured mortgage is less expensive.")
    else:
        print("\nBoth options have the same overall cost.")
    
    diff = str(round(abs(tot_cost_un - tot_cost_ins), 2))
    
    print("\nThe cost difference over the life of the loan is: $" + diff)
