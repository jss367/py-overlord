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
