
THIS_DIR=$(shell pwd)
RPMBUILD_DIR=${THIS_DIR}/os_xenapi/dom0/rpmbuild
PACKAGE=xenapi-plugins
VERSION_FILE=${THIS_DIR}/os_xenapi/dom0/etc/xapi.d/plugins/dom0_plugin_version.py
VERSION=$(shell awk '/PLUGIN_VERSION = / {gsub(/"/, ""); print $$3}' ${VERSION_FILE})

RPM_NAME=${PACKAGE}-${VERSION}-1.noarch.rpm

rpm: ${THIS_DIR}/output/${RPM_NAME}

${THIS_DIR}/output/${RPM_NAME}:
	mkdir -p ${THIS_DIR}/output
	mkdir -p ${RPMBUILD_DIR}
	@for dir in BUILD BUILDROOT SRPMS RPMS SPECS SOURCES; do \
	    rm -rf ${RPMBUILD_DIR}/$$dir; \
	    mkdir -p ${RPMBUILD_DIR}/$$dir; \
	done
	cp ${THIS_DIR}/os_xenapi/dom0/${PACKAGE}.spec ${RPMBUILD_DIR}/SPECS
	rm -rf /tmp/${PACKAGE}
	mkdir /tmp/${PACKAGE}
	cp -r ${THIS_DIR}/os_xenapi/dom0/etc/xapi.d /tmp/${PACKAGE}
	tar czf ${RPMBUILD_DIR}/SOURCES/${PACKAGE}-${VERSION}.tar.gz -C /tmp ${PACKAGE}
	rpmbuild -ba --nodeps --define "_topdir ${RPMBUILD_DIR}" --define "version ${VERSION}" ${RPMBUILD_DIR}/SPECS/${PACKAGE}.spec
	mv ${RPMBUILD_DIR}/RPMS/noarch/* ${THIS_DIR}/output


.PHONY: clean

clean:
	rm -rf ${RPMBUILD_DIR}