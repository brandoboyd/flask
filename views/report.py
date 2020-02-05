#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
UI for Channels

"""

from flask import (render_template)

from ..app import app
from ..utils.decorators import login_required


@app.route('/report')
@login_required()
def console_report(user):
    return render_template('/report.html',
        section = "report"
    )
