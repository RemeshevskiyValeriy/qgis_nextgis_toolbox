PLUGINNAME = qgis_avral

PY_FILES = \
	__init__.py \
	AlgorithmFactory.py \
	InputsDialog.py \
	NgPluginProviger.py \
	NgToolbox.py \
	NgToolboxPlugin.py \
	NgToolboxWindow.py \
	ResultsDialog.py

UI_FILES = \
	NgToolboxWindow.ui \
	ResultsDialog.ui

EXTRAS = metadata.txt icon.png LICENSE

COMPILED_RESOURCE_FILES = resources.py

# PLUGIN_UPLOAD = $(c)/plugin_upload.py

RESOURCE_SRC=$(shell grep '^ *<file' resources.qrc | sed 's@</file>@@g;s/.*>//g' | tr '\n' ' ')

compile:
	pyrcc5 -o resources.py resources.qrc
	lrelease i18n/*

zip: compile
	rm -f $(PLUGINNAME).zip
	mkdir -p .temp/$(PLUGINNAME)
	cp -vf $(PY_FILES) .temp/$(PLUGINNAME)
	cp -vf $(UI_FILES) .temp/$(PLUGINNAME)
	cp -vf $(COMPILED_RESOURCE_FILES) .temp/$(PLUGINNAME)
	cp -vf $(EXTRAS) .temp/$(PLUGINNAME)
	cp -vfr i18n .temp/$(PLUGINNAME)
	cd .temp && zip -r ../$(PLUGINNAME).zip $(PLUGINNAME)/*
	rm -rf .temp


# upload: zip
# 	@echo
# 	@echo "-------------------------------------"
# 	@echo "Uploading plugin to QGIS Plugin repo."
# 	@echo "-------------------------------------"
# 	$(PLUGIN_UPLOAD) $(PLUGINNAME).zip
