#!/usr/bin/env bash
find ./playbooks/ -name "*.yaml" -not -path "*/templates/*" -exec ansible-lint --nocolor {} +
