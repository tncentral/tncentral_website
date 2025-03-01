grep -oP 'INFO\: (\/\w*)+ accessed from \d+(\.\d+)+' logs/tncentral.log | perl -p -e 's/^INFO\: ((\/\w*)+) accessed from (\d+(\.\d+)+)$/$1\t$3/g'
