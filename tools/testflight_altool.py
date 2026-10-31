"""Require explicit Apple acceptance, even when altool incorrectly exits zero."""
import argparse
import os
import re
import subprocess


def require_success(operation, returncode, output):
    if operation not in ('validate', 'upload'):
        raise ValueError('Unknown altool operation')
    if returncode != 0:
        raise ValueError(f'Apple {operation} exited with status {returncode}')
    # Xcode 26.3 can return zero for a 409 validation rejection. Reject errors
    # even if the output also contains an earlier or contradictory success.
    if re.search(r'\bERROR\s*:|\b(?:UPLOAD|VERIFY|VALIDATION) FAILED\b|'
                 r'\bValidation failed\b|\bFailed to (?:upload|validate)\b', output, re.I):
        raise ValueError(f'Apple {operation} reported an error; acceptance is unverified')
    verb = 'validating' if operation == 'validate' else 'uploading'
    banner = 'VERIFY|VALIDATION' if operation == 'validate' else 'UPLOAD'
    confirmed = re.search(rf'^\s*(?:{banner}) SUCCEEDED with no errors\s*$', output, re.M)
    confirmed = confirmed or re.search(rf'\bNo errors {verb} archive at ', output)
    if not confirmed:
        raise ValueError(f'Apple {operation} did not explicitly confirm success')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['validate', 'upload'])
    parser.add_argument('--ipa', required=True)
    args = parser.parse_args()
    result = subprocess.run(
        ['xcrun', 'altool', '--'+args.operation+'-app', '--file', args.ipa,
         '--type', 'ios', '--apiKey', os.environ['ASC_KEY_ID'],
         '--apiIssuer', os.environ['ASC_ISSUER_ID'], '--output-format', 'normal'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False,
    )
    print(result.stdout, end='', flush=True)
    try:
        require_success(args.operation, result.returncode, result.stdout)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(f'Apple {args.operation} acceptance explicitly confirmed; processing remains unverified.')


if __name__ == '__main__':
    main()
