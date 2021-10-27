if [ ! -f ./vsc/code-server ]; then
wget https://github.com/cdr/code-server/releases/download/v3.12.0/code-server-3.12.0-linux-amd64.tar.gz -O vsc.tar.gz
mkdir ./vsc && tar -zxvf vsc.tar.gz -C ./vsc --strip-components 1
rm -rf vsc.tar.gz
fi

VSBASE=$(pwd)
IPADD=$(ifconfig | grep "inet " | grep "broadcast" | awk '{print $2}')
cd vsc
tmux kill-session -t $VSBASE
tmux new -s $VSBASE -d

for port in {8081..18081}
do
PORTCT=$(lsof -i -P -n | grep LISTEN | grep :$port | wc -l)
if [ $PORTCT = "0" ]; then
PORTUSE=$port
break
fi
done

tmux send -t $VSBASE "PASSWORD=1 ./code-server --host 0.0.0.0 --port $PORTUSE" Enter
echo http://$IPADD:$PORTUSE 2>&1 | tee ../url.log