"""Validate a commit message file or a bounded Git history; no dependencies."""
import argparse
import re
import subprocess
from pathlib import Path

SUBJECT = re.compile(r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9][a-z0-9/-]*\))?!?: \S.+$')
SHA = re.compile(r'^[0-9a-f]{40,64}$')


def valid(message):
    lines = message.strip().splitlines()
    if not lines:
        return False
    title = lines[0]
    if title.startswith(('Merge ', 'Revert "')):
        return True  # Standard Git-generated merge/revert messages.
    if not SUBJECT.fullmatch(title) or len(title) > 100 or title.endswith('.'):
        return False
    if '!' in title.split(': ', 1)[0] and not any(line.startswith('BREAKING CHANGE: ') and len(line) > 17 for line in lines[1:]):
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('message_file', nargs='?')
    parser.add_argument('--history', action='store_true')
    parser.add_argument('--base')
    args = parser.parse_args()
    if args.history:
        command = ['git', 'log', '--no-merges', '--format=%H%x00%B%x00']
        if args.base:
            if not SHA.fullmatch(args.base):
                parser.error('--base must be a full commit SHA')
            command.append(args.base + '..HEAD')
        data = subprocess.check_output(command).decode('utf-8').split('\0')
        messages = [(data[i].strip(), data[i+1]) for i in range(0, len(data)-1, 2)]
    elif args.message_file:
        messages = [('current', Path(args.message_file).read_text(encoding='utf-8-sig'))]
    else:
        parser.error('provide a message file or --history')
    failed = [identifier[:12] for identifier, message in messages if not valid(message)]
    if failed:
        raise SystemExit('Mensagem fora do padrão: ' + ', '.join(failed) + '. Use tipo(escopo): descrição; consulte CONTRIBUTING.md.')
    print(f'Conventional Commits: {len(messages)} mensagem(ns) válida(s).')


if __name__ == '__main__':
    main()
