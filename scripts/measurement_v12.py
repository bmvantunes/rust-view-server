"""Portable display arithmetic: integer totals; decimal round-half-even to six places.
Counts/timings/source bindings remain exact. No float accumulation or tolerances.
"""
from decimal import Decimal, localcontext, ROUND_HALF_EVEN

def rate(counts, nanoseconds):
    counts=list(counts);nanoseconds=list(nanoseconds)
    if len(counts)!=len(nanoseconds) or not counts: raise ValueError('sample dimensions')
    if any(type(x) is not int or x<0 for x in counts+nanoseconds): raise ValueError('nonnegative integers required')
    n=sum(counts);ns=sum(nanoseconds)
    if ns==0: raise ValueError('zero elapsed time')
    with localcontext() as ctx:
        ctx.prec=max(80,len(str(n))+len(str(ns))+20)
        display=(Decimal(n)*1_000_000_000/Decimal(ns)).quantize(Decimal('0.000001'),rounding=ROUND_HALF_EVEN)
    return {'count':n,'nanoseconds':ns,'per_second':str(display)}
