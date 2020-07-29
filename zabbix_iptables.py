#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Author: Seaky
# @Date:   2020/7/6 19:02


import argparse
import json
import re
from subprocess import run, PIPE, STDOUT

IPTABLES = '/sbin/iptables'


def execute(cmd, stdout=PIPE, stderr=STDOUT, encoding='utf-8', shell=False, *args, **kwargs):
    if isinstance(cmd, str):
        shell = True
    p = run(cmd, stdout=stdout, stderr=stderr, shell=shell, *args, **kwargs)
    if isinstance(p.stdout, bytes):
        p.stdout = p.stdout.decode(encoding)
    if isinstance(p.stderr, bytes):
        p.stderr = p.stderr.decode(encoding)
    return p


def get_items():
    data = []
    p1 = re.compile('Chain (?P<chain>\w+) \(policy')
    p2 = re.compile('^(?P<id>\d+)\s+(?P<pkts>\w+)\s+(?P<bytes>\w+)')
    p3 = re.compile('/\* ZABBIX (?P<comment>.*) \*/')

    for table in ['filter', 'nat']:
        p = execute('{} -t {} -nxvL --line-numbers'.format(IPTABLES, table))

        chain = ''
        for line in p.stdout.split('\n'):
            m1 = p1.search(line)
            if m1:
                chain = m1.group('chain')
                continue

            m2 = p2.search(line)
            if m2:
                d = m2.groupdict()
                d['chain'] = chain
                m3 = p3.search(line)
                if m3:
                    d['comment'] = m3.group('comment').strip()
                    d['name_type'] = 'comment'
                if not d.get('comment'):
                    d['comment'] = '{id}'.format(**d)
                    d['name_type'] = 'id'
                d['table'] = table.upper()
                d['name'] = '{table}_{chain}_{comment}'.format(**d)
                data.append(d)
    return data


def parse(key=None, unit='', table='', chain='', comment='', no_comment=False):
    items = get_items()
    if key:
        table, chain, *_ = key.split('_')
        comment = '_'.join(_)
    if not unit:
        return json.dumps(
            {'data': [{'{#IPTBS_ITEM}': x['name']} for x in items if no_comment or x['name_type'] == 'comment']})
    else:
        for x in items:
            if table.upper() == x['table'] and chain.upper() == x['chain'] and \
                    (comment.upper() == x['comment'].upper() or comment == x['id']):
                return x.get(unit)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--unit', default='', help='pkts/bytes')
    parser.add_argument('--table', default='', help='filter/nat')
    parser.add_argument('--chain', default='', help='input/output/forward/prerouting/postrouting')
    parser.add_argument('--comment', default='', help='comment/chain_id')
    parser.add_argument('--key', default='', help='zabbix discover key')
    parser.add_argument('--no_comment', action='store_true', help='discover items without "ZABBIX" in comment')
    args = parser.parse_args()

    print(parse(**args.__dict__))
