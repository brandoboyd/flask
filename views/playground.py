"""
    Playground
"""

from flask import render_template, request, redirect

from ..app              import app
from ..utils.decorators import superuser_required
from ..forms.playground import PostTextForm


@app.route('/test/playground')
@superuser_required
def playground_index(user):
    return redirect('/test/playground/chunker')


def choose_lang(content, lang, default='en'):
    from solariat.utils.lang.detect import detect_lang_code
    from solariat.utils.lang.support import LANG_MAP
    from solariat_nlp.languages import LangComponentFactory

    langs = {}
    langs["submitted"] = LANG_MAP.get(lang, "Auto Detect")
    lang_code_detected = detect_lang_code(content)
    langs["detected"] = LANG_MAP.get(lang_code_detected)

    if not lang or lang in {'detect', 'auto'}:
        lang = lang_code_detected

    if LangComponentFactory.is_lang_supported(lang):
        lang_used = lang
    elif LangComponentFactory.is_lang_supported(lang_code_detected):
        lang_used = lang_code_detected
    else:
        lang_used = default

    langs["used"] = LANG_MAP.get(lang_used)

    return lang_used, langs


@app.route("/test/playground/tagger", methods=['GET', 'POST'])
@superuser_required
def playground_tagger(user):
    from solariat_nlp.languages import LangComponentFactory

    from solariat_nlp.scoring import normalize_token

    posted_data = None  #example: 'mary had a little lamb'
    if request.method == 'POST':
        form = PostTextForm(request.form, csrf_enabled=False)
        if form.validate():
            posted_data = form.content.data
    else:
        form = PostTextForm()

    tagger_output = None
    lang_tpl_data = None

    if posted_data:
        lang = form.language.data
        lang_code, lang_tpl_data = choose_lang(posted_data, lang)
        provider = LangComponentFactory.resolve(lang_code)

        tagger = provider.get_tagger()
        tokenizer = provider.get_tokenizer()

        tokens = tokenizer.tokenize(posted_data)
        normalized_tokens = [normalize_token(token) for token in tokens]
        tagged_sent = [(token.lower(), tag) for token, tag in tagger.tag(normalized_tokens)]
        tagger_output = " ".join("%s/%s" % (token.lower(), tag) for token, tag in tagged_sent)

    return render_template(
        '/playground/tagger.html',
        top_level='test',
        parent = 'playground',
        section = 'test',
        name = 'playground_tagger',
        result = tagger_output,
        form = form,
        user = user,
        lang = lang_tpl_data
        )


@app.route("/test/playground/chunker", methods=['GET', 'POST'])
@superuser_required
def playground_chunker(user):
    from solariat_nlp.languages import LangComponentFactory

    from solariat_nlp.utils import extract_topics
    from solariat_nlp       import sa_labels
    from solariat.unidecode          import unidecode

    posted_data = None  #example: 'I need this shiny laptop'
    if request.method == 'POST':
        form = PostTextForm(request.form, csrf_enabled=False)
        if form.validate():
            posted_data = unidecode(form.content.data)
    else:
        form = PostTextForm()

    chunker_output = {}
    lang_tpl_data = None

    if posted_data:
        lang = form.language.data
        lang_code, lang_tpl_data = choose_lang(posted_data, lang)
        provider = LangComponentFactory.resolve(lang_code)
        chunker = provider.get_chunker()
        intention_type = sa_labels.SATYPE_NAME_TO_OBJ_MAP.get(
            posted_data.split(':')[0],
            None)

        if intention_type != None:
            intention_type = intention_type.title
            posted_data = posted_data[posted_data.find(":")+1:]

        tags = chunker.tag_content(posted_data)
        chunks, anchors, tree = chunker.parse(tags, intention_type)
        #print chunks, anchors
        chunker_output = {
            'chunks': '\n'.join(chunker.get_topics(chunks)),
            'topics': '\n'.join(extract_topics(posted_data, lang=lang_code)),
            'tree':tree.pprint(indent=8)
        }
        
    return render_template(
        '/playground/chunker.html',
        top_level='test',
        parent = 'playground',
        section = 'test',
        name = 'playground_chunker',
        result = chunker_output,
        form = form,
        user = user,
        lang = lang_tpl_data
        )
