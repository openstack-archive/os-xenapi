#!/bin/bash
# use conntrack statistic mode, so change conntrackd.conf
set -e

version=$(yum info conntrack-tools | grep '^Version' | awk '{print $3}')
conf_pro_all=$(find /usr/share/doc/conntrack-tools-$version -name \
               conntrackd.conf | grep stats)
if ! ls /etc/conntrackd/conntrackd.conf.back;  then
    cp -p /etc/conntrackd/conntrackd.conf /etc/conntrackd/conntrackd.conf.back
fi
cp -f $conf_pro_all /etc/conntrackd/

cat >/etc/logrotate.d/conntrackd <<EOF
/var/log/conntrackd*.log {
    daily
    maxsize 50M
    rotate 7
    copytruncate
    missingok
}
EOF

service conntrackd restart
