# -*- coding: utf-8 -*-

from accounts.forms import DisclaimerForm


class AdminDisclaimerForm(DisclaimerForm):

    def __init__(self, *args, **kwargs):
        super(AdminDisclaimerForm, self).__init__(*args, **kwargs)
        self.fields['password'].label = "Please have the user re-enter their " \
                                       "password to confirm acceptance of " \
                                        "the changes to their data."
