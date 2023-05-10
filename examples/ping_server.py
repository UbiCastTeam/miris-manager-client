#!/usr/bin/env python3
'''
Script to ping a Miris Manager server.
'''
import sys
from pathlib import Path


if __name__ == '__main__':
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from mm_client.client import MirisManagerClient

    local_conf = sys.argv[1] if len(sys.argv) > 1 else None
    mmc = MirisManagerClient(local_conf)
    # ping
    print(mmc.api_request('PING'))
