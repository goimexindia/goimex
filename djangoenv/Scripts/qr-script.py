#!E:\Users\admin\PycharmProjects\shubhshaadivivah\djangoenv\Scripts\python.exe
# EASY-INSTALL-ENTRY-SCRIPT: 'qrcode==7.2','console_scripts','qr'
__requires__ = 'qrcode==7.2'
import re
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw?|\.exe)?$', '', sys.argv[0])
    sys.exit(
        load_entry_point('qrcode==7.2', 'console_scripts', 'qr')()
    )
