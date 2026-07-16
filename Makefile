# Set variables BEFORE include — backend/Makefile uses ?= so these take priority
YAML_PATH=compose/local/compose.local.yaml

include backend/Makefile
