#!/usr/bin/env python

#
# This file is part of the `importscope` Python module
#
# Copyright 2026
# Daniele Bottazzi
#
# File author(s): Daniele Bottazzi (79707228+daniele-bottazzi@users.noreply.github.com)
#
# Distributed under the BSD-3-Clause license
# See the file `LICENSE` or read a copy at
# https://opensource.org/license/bsd-3-clause
#

"""Analyze Python import structure and render policy-aware dependency graphs."""

from .app import (
    check_repo,
    edit_config,
    init_config,
    show_config,
    analyze_repo,
    list_profiles,
    inspect_snapshot,
)
from ._metadata import __author__, __version__


__all__ = [
    '__author__',
    '__version__',
    'analyze_repo',
    'check_repo',
    'edit_config',
    'init_config',
    'inspect_snapshot',
    'list_profiles',
    'show_config',
]
