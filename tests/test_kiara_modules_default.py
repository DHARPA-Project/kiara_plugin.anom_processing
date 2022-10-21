#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `kiara_plugin.anom_processing` package."""

import kiara_plugin.anom_processing
import pytest  # noqa


def test_assert():

    assert kiara_plugin.anom_processing.get_version() is not None
