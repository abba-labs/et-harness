# Defect Backlog

No product defect or blocker remained after mechanical acceptance.

The first two baseline-capture attempts stopped before installer execution because
the running Gateway held `gateway.stderr.log` and `owner.lock` open. The final
collector hashed readable state files and compared locked files by path, length and
timestamp. This was an Evidence collection issue, not a Product or Runtime defect;
neither failed attempt invoked the installer or changed machine state.

No unsafe live PID-record forgery was performed against the stable Runtime. The
stop path's wrong-process checks are present, but this destructive negative case is
recorded as not mechanically injected into the live machine state.
