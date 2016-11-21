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
# Don't install the RPM as we may not have root.
rpm2cpio $DOM0_DIR/suppack/builder-rpms/supp-pack-build.rpm | cpio -idm
rpm2cpio $DOM0_DIR/suppack/builder-rpms/xcp-python-libs.rpm | cpio -idm
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
# Create os-xenapi-dom0-plugin RPM
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

# Remove temporary files used for building supplemental package
rm -rf ./usr
rm -f buildscript.py build-supplemental-pack.py build-supplemental-pack.sh suppack-install.py suppack-install.sh

# Restore xtrace
$_XTRACE_XENSERVER

echo ""
echo "Supplemental packages are built here: $BUILDROOT"