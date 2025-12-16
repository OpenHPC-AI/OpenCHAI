XCATROOT=/drbd/xcatdata/opt/xcat/
PATH=$XCATROOT/bin:$XCATROOT/sbin:$XCATROOT/share/xcat/tools:$PATH
MANPATH=$XCATROOT/share/man:$MANPATH
export XCATROOT PATH MANPATH
export PERL_BADLANG=0

# If /usr/local/share/perl5 is not already in @INC, add it to PERL5LIB
set +e
perl -e "print \"@INC\"" | egrep "(^|\W)/usr/local/share/perl5($| )" > /dev/null
PERL_FOUND=$?
set -e
if [ $? = 1 ]; then
    export PERL5LIB=/usr/local/share/perl5:$PERL5LIB
fi
