import base64
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import feedback

def fixture():
    return dict(id='a'*32,message='Damage differed in game.',profile_url='https://www.blablalink.com/shiftyspad?uid=YWJj',recommendation={'teams':[{'members':['demo']}]},owned_units=[{'id':'demo'}],ownership_basis='recommendation-time',squad=0,image={'type':'image/png','data':base64.b64encode(b'\x89PNG\r\n\x1a\nexample').decode()})

class FeedbackTests(unittest.TestCase):
    def test_valid_and_invalid_uploads(self):
        feedback.validate(fixture())
        for change in ({'squad':1},{'profile_url':'https://evil.test/'},{'owned_units':[]},{'message':''},{'token':'must not transmit secrets'},{'image':{'type':'image/svg+xml','data':base64.b64encode(b'<svg/>').decode()}},{'image':{'type':'image/png','data':'not base64'}}):
            with self.subTest(change=list(change)),self.assertRaises(ValueError):
                feedback.validate({**fixture(),**change})
        data=fixture();data['image']['data']=base64.b64encode(b'\x89PNG\r\n\x1a\n'+b'x'*2_000_000).decode()
        with self.assertRaises(ValueError):feedback.validate(data)

    def test_no_upload_without_configuration(self):
        with patch.object(feedback,'config',return_value={'enabled':False}),patch.object(feedback,'urlopen') as send:
            with self.assertRaisesRegex(ValueError,'not configured'):feedback.submit(fixture())
            send.assert_not_called()

    def test_confirmation_and_retry_identity(self):
        body=fixture()
        with patch.object(feedback,'config',return_value={'enabled':True,'endpoint':'https://script.google.com/macros/s/example/exec'}):
            for response in ({'ok':True,'id':body['id']},{'ok':True,'id':'wrong'},[],{'ok':False,'error':'Inbox busy.'}):
                with patch.object(feedback,'urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as send:
                    if isinstance(response,dict) and response.get('id')==body['id']:
                        self.assertEqual(feedback.submit(body),response)
                        self.assertEqual(json.loads(send.call_args.args[0].data),body)
                    else:
                        with self.assertRaises(ValueError):feedback.submit(body)
            with patch.object(feedback,'urlopen',side_effect=TimeoutError):
                with self.assertRaisesRegex(ValueError,'same form'):feedback.submit(body)

    def test_config_only_accepts_google_deployment(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(feedback,'ROOT',Path(tmp)):
            folder=Path(tmp)/'web';folder.mkdir();path=folder/'feedback-config.json'
            for value in ('http://127.0.0.1/internal','https://evil.test/',None):
                path.write_text(json.dumps({'endpoint':value}))
                self.assertFalse(feedback.config()['enabled'])
            path.write_text('{bad json')
            self.assertFalse(feedback.config()['enabled'])

if __name__=='__main__':unittest.main()
