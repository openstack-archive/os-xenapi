
THIS_DIR=$(shell pwd)
RPMBUILD_DIR=${THIS_DIR}/os_xenapi/dom0/contrib/rpmbuild
PACKAGE=xenapi-plugins
TMP_VERSION=$(shell grep "PLUGIN_VERSION = " ${THIS_DIR}/os_xenapi/dom0/etc/xapi.d/plugins/dom0_plugin_version.py |cut -d"=" -f2)
VERSION=$(shell echo ${TMP_VERSION} | sed 's/"//g')

RPM_NAME=${PACKAGE}-${VERSION}-1.noarch.rpm

rpm: ${THIS_DIR}/output/${RPM_NAME}

${THIS_DIR}/output/${RPM_NAME}:
	mkdir -p ${THIS_DIR}/output
	@for dir in BUILD BUILDROOT SRPMS RPMS SOURCES; do \
	    rm -rf ${RPMBUILD_DIR}/$$dir; \
	    mkdir -p ${RPMBUILD_DIR}/$$dir; \
	done
	rm -rf /tmp/${PACKAGE}
	mkdir /tmp/${PACKAGE}
	cp -r ${THIS_DIR}/os_xenapi/dom0/etc/xapi.d /tmp/${PACKAGE}
	tar czf ${RPMBUILD_DIR}/SOURCES/${PACKAGE}-${VERSION}.tar.gz -C /tmp ${PACKAGE}
	rpmbuild -ba --nodeps --define "_topdir ${RPMBUILD_DIR}" --define "version ${VERSION}" ${RPMBUILD_DIR}/${PACKAGE}.spec
	mv ${RPMBUILD_DIR}/RPMS/noarch/* ${THIS_DIR}/output


.PHONY: clean

clean:
	@for dir in BUILD BUILDROOT SRPMS RPMS SOURCES; do \
	    rm -rf ${RPMBUILD_DIR}/$$dir; \
	done
