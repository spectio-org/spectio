#!/bin/bash
sha=$1; q() { gh api repos/spectio-org/spectio/commits/$sha/check-runs --jq "$1" 2>/dev/null; }
until n=$(q '[.check_runs[]|select(.status!="completed")]|length') && [ "$n" = 0 ] && [ "$(q .total_count)" -gt 10 ]; do sleep 60; done
q '.check_runs[]|"\(.name) \(.conclusion)"' | sort | grep -v -E " (success|skipped)$"; echo SHA=$sha done
