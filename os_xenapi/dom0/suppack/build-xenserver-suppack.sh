#!/bin/bash

# Save trace setting
_XTRACE_XENSERVER=$(set +o | grep xtrace)
set -o xtrace

# =============================================
# Usage of this script:
# ./build-xenserver-suppack.sh os_release hypervisor xcp_version plugin_version
# or
# ./build-xenserver-suppack.sh
#
# You can provide explict input parameters or you can use the default ones:
#   os_release: OpenStack release branch
#   hypervisor: XenServer or other
#   xcp_version: Xen Platform version
#   plugin_version: OpenStack XenServer Plugin version

THIS_DIR=$(dirname $(readlink -f "$0"))
DOM0_DIR=$(dirname $THIS_DIR)
BUILDROOT=${DOM0_DIR}/build
rm -rf $BUILDROOT
mkdir -p $BUILDROOT && cd $BUILDROOT


# =============================================
# Configurable items

# OpenStack release
OS_RELEASE=${1:-"upstream"}

HYPERVISOR_NAME=${2:-"XenServer"}
PLATFORM_VERSION=${3:-"2.1"}

# nova and neutron xenserver dom0 plugin version
XS_PLUGIN_VERSION=${4:-"2.0"}

# Update system and install dependencies
export DEBIAN_FRONTEND=noninteractive


# =============================================
# Install suppack builder
RPM_ROOT=http://coltrane.uk.xensource.com/usr/groups/release/XenServer-7.x/XS-7.0/RTM-125380/binary-packages/RPMS/domain0/RPMS/noarch
wget $RPM_ROOT/supp-pack-build-2.1.0-xs55.noarch.rpm -O supp-pack-build.rpm
wget $RPM_ROOT/xcp-python-libs-1.9.0-159.noarch.rpm -O xcp-python-libs.rpm

# Don't install the RPM as we may not have root.
rpm2cpio supp-pack-build.rpm | cpio -idm
rpm2cpio xcp-python-libs.rpm | cpio -idm
# Work around dodgy requirements for xcp.supplementalpack.setup function
# Note that either root or a virtual env is needed here. venvs are better :)
cp -f usr/bin/* .

# If we are in a venv, we can potentially work with genisoimage and not mkisofs
venv_prefix=$(python -c 'import sys; print sys.prefix if hasattr(sys, "real_prefix") else ""')
set +e
mkisofs=`which mkisofs`
set -e
if [ -n "$venv_prefix" -a -z "$mkisofs" ]; then
    # Some systems (e.g. debian) only have genisofsimage.
    set +e
    genisoimage=`which genisoimage`
    set -e
    [ -n "$genisoimage" ] && ln -s $genisoimage $venv_prefix/bin/mkisofs
fi

# Now we must have mkisofs as the supp pack builder just invokes it
which mkisofs || (echo "mkisofs not installed" && exit 1)


# =============================================
# Create os-xenapi-dom0-plugin rpm file
pushd $DOM0_DIR/contrib
./build-rpm.sh $XS_PLUGIN_VERSION
popd

OS_XENAPI_RPMFILE=$(find $DOM0_DIR -name "os-xenapi-dom0-plugins-*.noarch.rpm" -print)


# =============================================
# Find conntrack-tools related RPMs
EXTRA_RPMS=""
EXTRA_RPMS="$EXTRA_RPMS $(find $DOM0_DIR -name "conntrack-tools-*.rpm" -print)"
EXTRA_RPMS="$EXTRA_RPMS $(find $DOM0_DIR -name "libnetfilter_cthelper-*.rpm" -print)"
EXTRA_RPMS="$EXTRA_RPMS $(find $DOM0_DIR -name "libnetfilter_cttimeout-*.rpm" -print)"
EXTRA_RPMS="$EXTRA_RPMS $(find $DOM0_DIR -name "libnetfilter_queue-*.rpm" -print)"


# =============================================
# Create Supplemental pack

tee buildscript.py << EOF
import sys
sys.path.append('$BUILDROOT/usr/lib/python2.7/site-packages')
from xcp.supplementalpack import *
from optparse import OptionParser

parser = OptionParser()
parser.add_option('--pdn', dest="product_name")
parser.add_option('--pdv', dest="product_version")
parser.add_option('--hvn', dest="hypervisor_name")
parser.add_option('--desc', dest="description")
parser.add_option('--bld', dest="build")
parser.add_option('--out', dest="outdir")
(options, args) = parser.parse_args()

xcp = Requires(originator='xcp', name='main', test='ge',
               product=options.hypervisor_name, version=options.product_version,
               build=options.build)

setup(originator='xcp', name=options.product_name, product=options.hypervisor_name,
      version=options.product_version, build=options.build, vendor='',
      description=options.description, packages=args, requires=[xcp],
      outdir=options.outdir, output=['iso'])
EOF

python buildscript.py \
--pdn=xenapi-plugins-$OS_RELEASE \
--pdv=$PLATFORM_VERSION \
--hvn="$HYPERVISOR_NAME" \
--desc="OpenStack os-xenapi plugins" \
--bld=0 \
--out=$BUILDROOT \
$OS_XENAPI_RPMFILE

python buildscript.py \
--pdn=conntrack-tools \
--pdv=$PLATFORM_VERSION \
--hvn="$HYPERVISOR_NAME" \
--desc="Dom0 conntrack-tools" \
--bld=0 \
--out=$BUILDROOT \
$EXTRA_RPMS

# Remove the unnecessary files
rm -rf ./usr
rm -f buildscript.py build-supplemental-pack.py build-supplemental-pack.sh suppack-install.py suppack-install.sh supp-pack-build.rpm xcp-python-libs.rpm

# Restore xtrace
$_XTRACE_XENSERVER

echo ""
echo "Supplemental packages are built here: $BUILDROOT"