"""Do not dispatch games for stale, overlapping or overwriting experiments."""
import json
from pathlib import Path

import pytest

from scripts import evaluate_remaining_card_policies as study


@pytest.mark.parametrize('problem', ['existing','missing','stale','overlap'])
def test_invalid_study_inputs_are_rejected_before_simulation(problem,tmp_path,monkeypatch,capsys):
    output=tmp_path/'validation.json'
    selection=tmp_path/'screen.json'
    data={'study':'optimizer','phase':'screen','simulation_fingerprint':'current',
          'runner_sha256':study.sha(Path(study.__file__)),
          'summary_helper_sha256':study.sha(Path(study.original.__file__)),
          'population':{'baseline':None,'candidate_0':{}},'selected':'candidate_0',
          'rows':[{'records':[{'seed':100}]}]}
    if problem=='stale':data['simulation_fingerprint']='previous'
    selection.write_text(json.dumps(data))
    args=['study','--study','optimizer','--phase','validate','--seed','100','--pairs','2','--output',str(output)]
    if problem!='missing':args+=['--selection',str(selection)]
    if problem=='existing':output.write_text('earlier outcomes')
    monkeypatch.setattr('sys.argv',args)
    monkeypatch.setattr(study,'tournament_fingerprint',lambda:'current')
    monkeypatch.setattr(study,'ProcessPoolExecutor',lambda **kw:pytest.fail('No games for invalid input'))
    with pytest.raises(SystemExit) as error:study.main()
    assert error.value.code==2
    assert {'existing':'evidence exists','missing':'frozen screen','stale':'Stale screen','overlap':'seeds overlap'}[problem] in capsys.readouterr().err
    assert output.read_text()=='earlier outcomes' if output.exists() else problem!='existing'


@pytest.mark.parametrize('changed', ['policy', 'reaction', 'summary'])
def test_guide_rejects_changed_evaluation_runners(tmp_path, monkeypatch, changed):
    from scripts import render_remaining_card_policies_guide as guide
    names = ('investment-accounting-screen', 'investment-accounting-validation',
             'investment-registered-validation', 'contextual-policy-search-screen',
             'contextual-policy-search-validation', 'gain-effect-ordering-reaction-validation')
    metadata = {'simulation_fingerprint': 'current',
                'runner_sha256': study.sha(Path(study.__file__)),
                'summary_helper_sha256': study.sha(Path(study.original.__file__)),
                'evaluator_sha256': study.sha(Path('scripts/evaluate_reaction_duration_tactics.py'))}
    field = {'policy': 'runner_sha256', 'reaction': 'evaluator_sha256', 'summary': 'summary_helper_sha256'}[changed]
    metadata[field] = 'stale'
    for name in names:
        data = dict(metadata)
        if name.endswith('validation') and name.startswith(('investment-accounting', 'contextual-policy')):
            previous = tmp_path / (name.replace('-validation', '-screen') + '.json')
            data['selection_sha256'] = study.sha(previous)
        (tmp_path / (name + '.json')).write_text(json.dumps(data))
    monkeypatch.setattr(guide, 'DATA', tmp_path)
    monkeypatch.setattr(guide, 'tournament_fingerprint', lambda: 'current')
    with pytest.raises(ValueError, match={'policy': 'Policy runner', 'reaction': 'Reaction runner', 'summary': 'Summary helper'}[changed]):
        guide.render()
