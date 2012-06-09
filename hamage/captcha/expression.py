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

from trac.core import *
from trac.config import *
from trac.util.html import html, Markup
from tracspamfilter.captcha import ICaptchaMethod


class ExpressionCaptcha(Component):
    """captcha in the form of a human readable numeric expression
    
    Initial implementation by sergeych@tancher.com.
    """

    implements(ICaptchaMethod)

    terms = IntOption('spam-filter', 'captcha_expression_terms', 3,
            """Number of terms in numeric CAPTCHA expression.""")

    ceiling = IntOption('spam-filter', 'captcha_expression_ceiling', 10,
            """Maximum value of individual terms in numeric CAPTCHA
            expression.""")

    operations = {'*': 'multiplied by', '-': 'minus', '+': 'plus'}

    numerals = ('zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven',
                'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen',
                'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen',
                'nineteen' )

    tens = ('twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy',
            'eighty', 'ninety')

    # ICaptchaMethod methods

    def generate_captcha(self, req):
        if self.ceiling > 100:
            raise TracError('Numeric captcha can not represent numbers > 100')
        terms = [str(random.randrange(0, self.ceiling)) 
                 for i in xrange(self.terms)]
        operations = [random.choice(self.operations.keys()) 
                      for i in xrange(self.terms)]
        expression = sum(zip(terms, operations), ())[:-1]
        expression = eval(compile(' '.join(expression), 'captcha_eval', 'eval'))
        human = sum(zip([self._humanise(int(t)) for t in terms],
                        [self.operations[o] for o in operations]), ())[:-1]
        return (expression, html.blockquote(' '.join(map(str, human))))

    def verify_captcha(self, req):
        return False

    def is_usable(self, req):
        return True

    # Internal methods
    
    def _humanise(self, value):
        if value < 20:
            return self.numerals[value]
        english = self.tens[value / 10 - 2]
        if value % 10:
            english += ' ' + self.numerals[value % 10]
        return english
