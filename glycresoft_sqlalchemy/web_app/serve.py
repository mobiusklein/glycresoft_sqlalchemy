import logging
try:
    logging.basicConfig(level='DEBUG')
except:
    pass
import json
import functools
from glycresoft_sqlalchemy.web_app import report
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash, Markup, make_response, jsonify, \
     Response

from werkzeug import secure_filename
import argparse
import random
from glycresoft_sqlalchemy.data_model import (Hypothesis, Protein, TheoreticalGlycopeptide,
                                              GlycopeptideMatch, HypothesisSampleMatch, json_type)
from glycresoft_sqlalchemy.report import microheterogeneity
from glycresoft_sqlalchemy.web_app.project_manager import ProjectManager

from glycresoft_sqlalchemy.web_app.task.do_bupid_yaml_parse import BUPIDYamlParseTask
from glycresoft_sqlalchemy.web_app.task.do_decon2ls_parse import Decon2LSIsosParseTask
from glycresoft_sqlalchemy.web_app.task.do_ms2_search import TandemMSGlycoproteomicsSearchTask
from glycresoft_sqlalchemy.web_app.task.task_process import QueueEmptyException

app = Flask(__name__)
report.prepare_environment(app.jinja_env)

DATABASE = None
DEBUG = False
SECRETKEY = 'TG9yZW0gaXBzdW0gZG90dW0'

manager = None


JSONEncoderType = json_type.new_alchemy_encoder()


def connect_db():
    g.db = manager.session()


def message_queue_stream():
    """Implement a simple Server Side Event (SSE) stream based on the
    stream of events emit from the :attr:`TaskManager.messages` queue of `manager`.

    These messages are handled on the client side.

    Yields
    ------
    str: Formatted Server Side Event Message

    References
    ----------
    [1] - http://stackoverflow.com/questions/12232304/how-to-implement-server-push-in-flask-framework
    """
    payload = 'id: {id}\nevent: {event_name}\ndata: {data}\n\n'
    i = 0
    yield payload.format(id=i, event_name='begin-stream', data=json.dumps('Starting Stream'))
    yield payload.format(id=i - 1, event_name='update', data=json.dumps('Initialized'))
    i += 1
    while True:
        try:
            message = manager.messages.get(True, 3)
            event = payload.format(
                id=i, event_name=message.type,
                data=json.dumps(message.message))
            i += 1
            print message, event
            yield event
        except KeyboardInterrupt:
            break
        except QueueEmptyException, e:
            # Send a comment to keep the connection alive
            if random.random() > 0.8:
                yield payload.format(id=i, event_name='tick', data=json.dumps('Tick'))
        except Exception, e:
            logging.exception("An error occurred in message_queue_stream", exc_info=e)


@app.route("/")
def index():
    return render_template("index.templ")


@app.route('/stream')
def message_stream():
    return Response(message_queue_stream(),
                    mimetype="text/event-stream")


# ----------------------------------------
#           Settings and Preferences
# ----------------------------------------


@app.route("/preferences")
def show_preferences():
    preferences = request.values
    return render_template("components/preferences.templ", **preferences)


@app.route("/preferences", methods=["POST"])
def update_preferences():
    preferences = request.values
    print "Minimum Score:", preferences["minimum_score"]
    print request.values
    return jsonify(**preferences)


@app.route("/internal/update_settings", methods=["POST"])
def update_settings():
    '''
    TODO
    ----
    Diff incoming settings with server-side settings and
    send back the union of the settings to the client.
    '''
    settings = request.values
    return jsonify(**settings)


@app.route("/test/task-test")
def test_page():
    protein = g.db.query(Protein).join(GlycopeptideMatch).first()

    def filter_context(q):
        return q.filter(
            GlycopeptideMatch.ms2_score > 0.2)

    return render_template("test.templ", protein=protein, filter_context=filter_context)


# ----------------------------------------
#           View Database Search Results
# ----------------------------------------


@app.route("/view_database_search_results/<int:id>")
def view_database_search_results(id):
    hsm = g.db.query(HypothesisSampleMatch).get(id)
    hypothesis_sample_match_id = id

    def filter_context(q):
        return q.filter_by(
            hypothesis_sample_match_id=hypothesis_sample_match_id).filter(
            GlycopeptideMatch.ms2_score > 0.2)

    return render_template(
        "view_database_search_results.templ",
        hsm=hsm,
        filter_context=filter_context)


@app.route("/view_database_search_results/protein_view/<int:id>", methods=["POST"])
def view_protein_results(id):
    print request.values
    hypothesis_sample_match_id = request.values["hypothesis_sample_match_id"]
    protein = g.db.query(Protein).get(id)

    def filter_context(q):
        return q.filter_by(
            hypothesis_sample_match_id=hypothesis_sample_match_id).filter(
            GlycopeptideMatch.ms2_score > 0.2)

    site_summary = microheterogeneity.GlycoproteinMicroheterogeneitySummary(
        protein, filter_context)

    return render_template(
        "components/protein_view.templ",
        protein=protein,
        site_summary=site_summary,
        filter_context=filter_context)


@app.route("/view_database_search_results/view_glycopeptide_details/<int:id>")
def view_glycopeptide_details(id):
    gpm = g.db.query(GlycopeptideMatch).get(id)
    return render_template(
        "components/glycopeptide_details.templ", glycopeptide=gpm)


# ----------------------------------------
#           JSON Data API Calls
# ----------------------------------------


@app.route("/api/glycopeptide_matches/<int:id>")
def get_glycopeptide_match_api(id):
    gpm = g.db.query(GlycopeptideMatch).get(id)
    return Response(JSONEncoderType().encode(gpm), mimetype="text/json")


@app.route("/api/tasks")
def api_tasks():
    return jsonify(**{t.id: t.to_json() for t in manager.tasks.values()})


@app.route("/api/hypothesis_sample_matches")
def api_hypothesis_sample_matches():
    hsms = g.db.query(HypothesisSampleMatch).all()
    d = {str(h.id): h.to_json() for h in hsms}
    return jsonify(**d)


@app.route("/api/hypotheses")
def api_hypothesis():
    hypotheses = g.db.query(Hypothesis).all()
    d = {str(h.id): h.to_json() for h in hypotheses}
    return jsonify(**d)


@app.route("/api/samples")
def api_samples():
    samples = manager.samples()
    d = {str(h.name): h.to_json() for h in samples}
    return jsonify(**d)


# ----------------------------------------
#
# ----------------------------------------


@app.route("/hypothesis")
def show_hypotheses():
    return render_template("show_hypotheses.templ", hypotheses=g.db.query(Hypothesis).all())


@app.route("/view_hypothesis/<int:id>")
def view_hypothesis(id):
    return render_template("show_hypotheses.templ", hypotheses=[g.db.query(Hypothesis).get(id)])


# ----------------------------------------
#
# ----------------------------------------


@app.route("/glycan_search_space")
def build_naive_glycan_search():
    return render_template("glycan_search_space.templ")


# ----------------------------------------
#
# ----------------------------------------


@app.route("/glycan_search_space", methods=["POST"])
def build_naive_glycan_search_process():
    print request.values
    return jsonify(**dict(request.values))


# ----------------------------------------
#
# ----------------------------------------


@app.route("/glycopeptide_search_space")
def build_naive_glycopeptide_search_space():
    return render_template("glycopeptide_search_space.templ")


@app.route("/glycopeptide_search_space", methods=["POST"])
def build_naive_glycopeptide_search_space_post():
    print request.values.__dict__
    print request.files
    values = request.values
    constant_modifications = values.getlist("constant_modifications")
    variable_modifications = values.getlist("variable_modifications")
    enzyme = values.getlist("enzyme")
    hypothesis_name = values.get("hypothesis_name")
    protein_fasta = request.files["protein-fasta-file"]
    site_list = request.files["glycosylation-site-list-file"]
    glycan_file = request.files["glycan-definition-file"]
    glycan_file_type = values.get("glycans-file-format")

    print(constant_modifications,
          variable_modifications,
          enzyme,
          hypothesis_name,
          protein_fasta,
          site_list,
          glycan_file,
          glycan_file_type,)

    return jsonify(status=202)


# ----------------------------------------
#
# ----------------------------------------


@app.route("/tandem_match_samples")
def tandem_match_samples():
    return render_template("tandem_match_samples.templ")


@app.route("/tandem_match_samples", methods=["POST"])
def tandem_match_samples_post():
    user_parameters = request.values
    job_parameters = {
        "ms1_tolerance": float(user_parameters["ms1-tolerance"]) * 1e-6,
        "ms2_tolerance": float(user_parameters["ms2-tolerance"]) * 1e-6,
        "target_hypothesis_id": int(user_parameters["hypothesis_choice"]),
        "database_path": manager.path

    }
    db = manager.session()
    target_hypothesis = db.query(Hypothesis).get(user_parameters["hypothesis_choice"])
    decoy_id = target_hypothesis.parameters["decoys"][0]["hypothesis_id"]
    job_parameters['decoy_hypothesis_id'] = decoy_id

    print request.values.__dict__

    for sample_name in request.values.getlist('samples'):
        instance_parameters = job_parameters.copy()
        sample_run, sample_manager = manager.find_sample(sample_name)
        instance_parameters["observed_ions_path"] = sample_manager.path
        instance_parameters["sample_run_id"] = sample_run.id
        instance_parameters['callback'] = lambda: 0
        instance_parameters['observed_ions_type'] = 'db'
        print instance_parameters
        task = TandemMSGlycoproteomicsSearchTask(**instance_parameters)
        manager.add_task(task)
    return jsonify(**dict(request.values))

# ----------------------------------------
#
# ----------------------------------------


@app.route("/add_sample", methods=["POST"])
def post_add_sample():
    """Handle an uploaded sample file

    Returns
    -------
    TYPE : Description
    """
    print request.values
    run_name = request.values['sample_name']
    secure_name = secure_filename(run_name)

    secure_name += ".%s" % request.values["file-type"]
    path = manager.get_temp_path(secure_name)
    request.files['observed-ions-file'].save(path)
    dest = manager.get_sample_path(run_name)
    # Construct the task with a callback to add the processed sample
    # to the set of project samples
    callback = functools.partial(manager.add_sample, path=dest)
    task_type = None
    print request.values["file-type"], type(request.values["file-type"])
    if request.values["file-type"] == "decon2ls":
        task_type = Decon2LSIsosParseTask
    elif request.values["file-type"] == "bupid":
        task_type = BUPIDYamlParseTask
    task = task_type(
        manager.path,
        path,
        dest,
        callback)
    manager.add_task(task)
    return redirect("/")


@app.route("/add_sample")
def add_sample():
    return render_template("add_sample_form.templ")


# ----------------------------------------
#
# ----------------------------------------


@app.before_request
def before_request():
    connect_db()


@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


@app.context_processor
def inject_model():
    return {
        "Hypothesis": Hypothesis,
        "Protein": Protein,
        "TheoreticalGlycopeptide": TheoreticalGlycopeptide,
        "GlycopeptideMatch": GlycopeptideMatch,
        "Manager": manager
    }


@app.context_processor
def inject_functions():
    def query(args):
        return g.db.query(args)
    return locals()

parser = argparse.ArgumentParser('view-results')
parser.add_argument("results_database")
parser.add_argument("-n", "--no-execute-tasks", action="store_true", required=False, default=False)
parser.add_argument("--external", action='store_true', requied=False, default=False, help='Let non-host machines connect to the server')


def main():
    args = parser.parse_args()
    results_database = args.results_database
    global DATABASE, manager, CAN_EXECUTE
    host = None
    if args.external:
        host = "0.0.0.0"
    DATABASE = results_database
    CAN_EXECUTE = not args.no_execute_tasks
    manager = ProjectManager(DATABASE)
    app.debug = DEBUG
    app.secret_key = SECRETKEY
    app.run(host=host, use_reloader=False, threaded=True, debug=DEBUG)

if __name__ == "__main__":
    main()
