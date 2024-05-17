# This file is part of the OpenADK project. OpenADK is copyrighted
# material, please see the LICENCE file in the top-level directory.

include $(ADK_TOPDIR)/rules.mk

PKG_NAME:=			threads
PKG_VERSION:=		1.0
PKG_RELEASE:=		1
PKG_DESCR:=			package for the threads CSCG 2024 challenge
PKG_SECTION:=		base/apps

WRKDIST=		$(WRKDIR)/$(PKG_NAME)
NO_DISTFILES:=		1

include $(ADK_TOPDIR)/mk/package.mk

$(eval $(call PKG_template,THREADS,threads,$(PKG_VERSION)-$(PKG_RELEASE),$(PKG_DEPENDS),$(PKG_DESCR),$(PKG_SECTION)))

CONFIG_STYLE:=		manual
BUILD_STYLE:=		manual
INSTALL_STYLE:=		manual

do-build:
	cd $(WRKBUILD) && CC='$(TARGET_CC)' CFLAGS='$(TARGET_CFLAGS)' \
	    CPPFLAGS='$(TARGET_CPPFLAGS)' LDFLAGS='$(TARGET_LDFLAGS)' \
	    HAVE_CAN_FSTACKPROTECTORALL=0 HAVE_CAN_FSTACKPROTECTORSTRONG=0 \
	    TARGET_OS=Linux $(MAKE)

threads-install:
	$(INSTALL_DIR) $(IDIR_THREADS)/usr/bin
	$(INSTALL_BIN) $(WRKBUILD)/threads $(IDIR_THREADS)/usr/bin
	$(INSTALL_DIR) $(IDIR_THREADS)/root/files/
	$(CP) $(WRKBUILD)/files/* $(IDIR_THREADS)/root/files
	$(INSTALL_DIR) $(IDIR_THREADS)/etc
	$(CP) $(WRKBUILD)/banner $(IDIR_THREADS)/etc

include $(ADK_TOPDIR)/mk/pkg-bottom.mk
