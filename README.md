# 1Blu DDNS


## Gettings Started

This service can be easily run as a docker container.


## Environment Variables

<code>USERNAME</code> Your 1Blu username

<code>PASSWORD</code> Your 1Blu password

<code>OTP_KEY</code> (optional) Your 1Blu OTP key. If you don't have 2-factor authentification activated on your account, this can be omitted. Note: this is not the key that is used to log into your account but the one which is generated when 2fa is activated.

<code>CONTRACT</code> The Contract Number of your 1Blu account. It can be found at https://ksb.1blu.de/products/ under Vertrags-No.

<code>DOMAIN_NUMBER</code> The domain number. To retrieve this, navigate to the dns editor. Now the domain numebr can be found in the url: https://ksb.1blu.de/\<contract-number\>/domain/\<domain-number\>/dns/ 

<code>DOMAIN</code> The domain without the subdomain. For example: "example.de" 

<code>SUBDOMAIN</code> (optional) The subdomain. If omitted, the maindomain will be used.

<code>RRTYPE</code> (optional) The rrtype. Can be either A (default) for ipv4 or AAAA for ipv6.


<code>INTERVAL</code> (optional) The interval between update tries in minutes. Defaults to 180. 

<code>LOGGING_LEVEL</code> (optional) The logging level. Can be one of the following:
- INFO (default): info, warnings and errors will be logged.
- WARNING: warnings and rrrors will be logged.
- ERROR: only errors will be logged
- DEBUG: info, warning, errors and debug messages will be logged.

