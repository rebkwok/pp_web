[![Build Status](https://travis-ci.org/rebkwok/pp_web.svg?branch=master)](https://travis-ci.org/rebkwok/pp_web)
[![Coverage Status](https://coveralls.io/repos/rebkwok/pp_web/badge.svg)](https://coveralls.io/r/rebkwok/pp_web)


# Pole Performance website

# Local development

Vagrant provisioning requires ansible 2.1.1.0 AND python 2.7

# Required settings

- SECRET_KEY: app secret key
- DATABASE_URL: database settings
- LOG_FOLDER: path to folder containing the app's log files
- EMAIL_HOST_PASSWORD: password for emails sent from the app
- DEFAULT_PAYPAL_EMAIL: the email address paypal payments made through the app will be sent to
- DEFAULT_STUDIO_EMAIL
- SIMPLECRYPT_PASSWORD
- ENTRIES_OPEN_DATE: in dd/mm/yyyy format (e.g. 31/08/2016)
- ENTRIES_CLOSE_DATE: in dd/mm/yyyy format
- CURRENT_ENTRY_YEAR: in yyyy format

# Optional for dev
- USE_MAILCATCHER: Boolean, set to True to send mail to mailcatcher
- DEBUG: False for dev
- PAYPAL_TEST=True

