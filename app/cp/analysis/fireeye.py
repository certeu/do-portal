"""
    CP FireEye Dynamic analysis endpoint
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
from flask_jsonschema import validate

from app.api.analysis.fireeye import process_add_fireeye_url_analysis, process_get_fireeye_analysis, \
    process_get_fireeye_report, process_add_fireeye_analysis, process_get_fireeye_environments
from app.cp import cp


@cp.route('/analysis/fireeye/report/<string:sha256>/<int:rid>', methods=['GET'])
def get_cp_fireeye_report(sha256, rid):
    return process_get_fireeye_report(sha256, rid, only_current_user=True)


@cp.route('/analysis/fireeye/<string:sha256>/<int:sid>', methods=['GET'])
def get_cp_fireeye_analysis(sha256, sid):
    return process_get_fireeye_analysis(sha256, sid, only_current_user=True)


@cp.route('/analysis/fireeye', methods=['POST', 'PUT'])
def add_cp_fireeye_analysis():
    return process_add_fireeye_analysis()


@cp.route('/analysis/fireeye-url', methods=['POST', 'PUT'])
@validate('analysis', 'add_fireeye_url_analysis')
def add_cp_fireeye_url_analysis():
    return process_add_fireeye_url_analysis()


@cp.route('/analysis/fireeye/environments')
def get_cp_fireeye_environments():
    return process_get_fireeye_environments()
