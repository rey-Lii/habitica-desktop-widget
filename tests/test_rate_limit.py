import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from habitica_core import API, RateLimitError, retry_delay

class RateLimitTests(unittest.TestCase):
    def test_header_seconds(self): self.assertEqual(retry_delay('45'),46)
    def test_header_http_date(self): self.assertEqual(retry_delay('Thu, 01 Jan 1970 00:01:00 GMT',now=10),51)
    def test_missing_or_invalid_header(self):
        for value in (None,'invalid','-2','nan','inf'):
            self.assertEqual(retry_delay(value),121)
    def test_cooldown_blocks_reads_and_writes(self):
        api=API('uid','token')
        err=HTTPError('https://habitica.com',429,'Too many requests',{'Retry-After':'30'},None)
        with patch('habitica_core.time.monotonic',return_value=100), patch('habitica_core.urlopen',side_effect=err) as fetch:
            with self.assertRaises(RateLimitError): api.request('POST','/tasks/task/score/up')
            self.assertEqual(api.cooldown_remaining(),31)
            for method in ('GET','POST'):
                with self.assertRaises(RateLimitError): api.request(method,'/tasks/user')
            self.assertEqual(fetch.call_count,1)
        with patch('habitica_core.time.monotonic',return_value=131): self.assertEqual(api.cooldown_remaining(),0)
    def test_no_automatic_write_replay(self):
        api=API('uid','token')
        err=HTTPError('https://habitica.com',429,'Too many requests',{},None)
        with patch('habitica_core.time.monotonic',return_value=100), patch('habitica_core.urlopen',side_effect=err) as fetch:
            with self.assertRaises(RateLimitError): api.request('POST','/tasks/task/score/up')
            self.assertEqual(fetch.call_count,1)
            self.assertEqual(api.cooldown_remaining(),121)

if __name__=='__main__': unittest.main()
