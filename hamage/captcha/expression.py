# -*- coding: utf-8 -*-
#
# Copyright (C) 2006 Edgewall Software
# Copyright (C) 2006 Alec Thomas <alec@swapoff.org>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://trac.edgewall.com/license.html.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://projects.edgewall.com/trac/.
#
# Author: Alec Thomas <alec@swapoff.org>

import random

from trac.util.html import html, Markup

operation_names = {'*': 'multiplied by', '-': 'minus', '+': 'plus'}

numerals = (
    'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven',
    'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen',
    'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen',
    'nineteen' )

tens = ('twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy',
        'eighty', 'ninety')


def _interleave(list1, list2):
    """This creates a list of [list1[0], list2[0], list1[1], list2[1], ...]

    If length is unequal, stop at length of shorter list.
    """
    return list(sum(zip(list1, list2), ()))


def _make_expression(terms, operations):
    assert len(operations) == len(terms) - 1
    # To interleave we want the same length.
    expression = _interleave(terms, operations + ['unused'])[:-1]
    expression = eval(compile(' '.join(expression), 'captcha_eval', 'eval'))
    return expression


def _humanize_expression(terms, operations):
    expression = _make_expression(terms, operations)
    # To interleave we want the same length.
    op_names = [operation_names[o] for o in operations] + ['unused']
    human = _interleave([_humanise(int(t)) for t in terms], op_names)[:-1]
    return expression, human

def _humanise(value):
    if value < 20:
        return numerals[value]
    english = tens[value / 10 - 2]
    if value % 10:
        english += ' ' + numerals[value % 10]
    return english


class ExpressionCaptcha(object):
    """captcha in the form of a human readable numeric expression

    Initial implementation by sergeych@tancher.com.
    """

    is_captcha = True

    def __init__(self, config):
        self.config = config
        # Number of terms in numeric CAPTCHA expression.
        self.terms = config.get('captcha_expression_terms', 3)
        # Maximum value of individual terms in numeric CAPTCHA expression.
        self.ceiling = config.get('captcha_expression_ceiling', 10)
        if self.ceiling > 100:
            raise ValueError('Numeric captcha can not represent numbers > 100')

    def generate_captcha(self, req):
        terms = [str(random.randrange(0, self.ceiling)) 
                 for i in xrange(self.terms)]
        operations = [random.choice(operation_names.keys()) 
                      for i in xrange(self.terms -1)]
        expression, human = _humanize_expression(terms, operations)
        return (expression, html.blockquote(' '.join(map(str, human))))

    def verify_captcha(self, req):
        # Um, this should do something.
        return False

    def is_usable(self, req):
        return True

