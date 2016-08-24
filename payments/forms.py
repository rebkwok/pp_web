from django.utils.safestring import mark_safe
from paypal.standard.forms import PayPalPaymentsForm


class PayPalPaymentsListForm(PayPalPaymentsForm):

    def get_image(self):
        super(PayPalPaymentsListForm, self).get_image()
        return {
            (True, self.SUBSCRIBE): 'https://www.paypalobjects.com/webstatic/en_US/i/btn/png/gold-pill-paypal-26px.png',
            (True, self.BUY): 'https://www.paypalobjects.com/webstatic/en_US/i/btn/png/gold-pill-paypal-26px.png',
            (True, self.DONATE): 'https://www.paypalobjects.com/webstatic/en_US/i/btn/png/gold-pill-paypal-26px.png',
            (False, self.SUBSCRIBE): 'https://www.paypalobjects.com/webstatic/en_US/btn/btn_subscribe_113x26.png',
            (False, self.BUY): 'https://www.paypalobjects.com/webstatic/en_US/btn/btn_buynow_pp_142x27.png',
            (False, self.DONATE): 'https://www.paypalobjects.com/webstatic/en_US/btn/btn_donate_pp_142x27.png',
        }[self.test_mode(), self.button_type]

    def render(self):
        super(PayPalPaymentsListForm, self).render()
        return mark_safe(u"""<form class="paypal-btn-form" action="%s" method="post">
            %s
        <input class="paypal-table-btn" type="image" src="%s" border="0" name="submit" alt="Paypal" />
        </form>""" % (self.get_endpoint(), self.as_p(), self.get_image()))


class PayPalPaymentsVideoForm(PayPalPaymentsForm):

    def get_image(self):
        super(PayPalPaymentsVideoForm, self).get_image()
        return {
            (True, self.SUBSCRIBE): 'https://www.paypalobjects.com/webstatic/en_US/i/btn/png/gold-pill-paypal-44px.png',
            (True, self.BUY): 'https://www.paypalobjects.com/webstatic/en_US/i/btn/png/gold-pill-paypal-44px.png',
            (True, self.DONATE): 'https://www.paypalobjects.com/webstatic/en_US/i/btn/png/gold-pill-paypal-44px.png',
            (False, self.SUBSCRIBE): 'https://www.paypalobjects.com/webstatic/en_US/btn/btn_subscribe_113x26.png',
            (False, self.BUY): 'https://www.paypalobjects.com/webstatic/en_US/btn/btn_buynow_pp_142x27.png',
            (False, self.DONATE): 'https://www.paypalobjects.com/webstatic/en_US/btn/btn_donate_pp_142x27.png',
        }[self.test_mode(), self.button_type]

    def render(self):
        super(PayPalPaymentsVideoForm, self).render()
        return mark_safe(u"""<form class="paypal-btn-form" action="%s" method="post">
            %s
        <input type="image" src="%s" border="0" name="submit" alt="Paypal" />
        </form>""" % (self.get_endpoint(), self.as_p(), self.get_image()))


