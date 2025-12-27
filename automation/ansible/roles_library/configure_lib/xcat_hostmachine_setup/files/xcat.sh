XCATROOT="/drbd/xcatdata/opt/xcat"

# Only configure xCAT environment if DRBD is mounted and xCAT exists
if [ -d "$XCATROOT" ] && mountpoint -q /drbd; then
    export XCATROOT
    export PATH="$XCATROOT/bin:$XCATROOT/sbin:$XCATROOT/share/xcat/tools:$PATH"
    export MANPATH="$XCATROOT/share/man:${MANPATH:-}"
fi

# Perl environment (safe, non-fatal)
if command -v perl >/dev/null 2>&1; then
    perl -e 'exit(grep { $_ eq "/usr/local/share/perl5" } @INC ? 0 : 1)' 2>/dev/null
    if [ $? -ne 0 ]; then
        export PERL5LIB="/usr/local/share/perl5:${PERL5LIB:-}"
    fi
fi

export PERL_BADLANG=0
