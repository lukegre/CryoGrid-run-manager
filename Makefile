
# some makefile magic commands
.DEFAULT_GOAL := help
.PHONY: help


env:  ## creates a python environment from the pyproject.toml file
	@uv sync --all-extras


fetch-cryogrid-source:  ## downloads the ./source folder from https://github.com/sebastianwestermann/CryoGrid.git 
	@if [ -d "src/matlab/source" ]; then echo "CryoGrid source code is already downloaded"; else $(MAKE) download-cryogrid-source; fi;


download-cryogrid-source:  
	git clone --depth 1 --single-branch --branch master https://github.com/sebastianwestermann/CryoGrid.git 
	mv -f CryoGrid/source ./src/matlab/source 
	rm -rf CryoGrid 

force-download-cryogrid-source:  
	rm -rf CryoGrid 
	rm -rf src/matlab/source
	$(MAKE) _download-cryogrid-source

init:  env fetch-cryogrid-source  ## initializes the package by creating the environment and fetching the CryoGrid source code


help:  ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

