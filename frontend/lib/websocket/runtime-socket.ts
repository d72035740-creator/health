export type RuntimeConnectionState="CONNECTING"|"CONNECTED"|"RECONNECTING"|"DISCONNECTED";
const url=(process.env.NEXT_PUBLIC_API_BASE_URL??"http://localhost:8000").replace(/^http/,"ws")+"/ws/runtime";
export function connectRuntimeSocket(onUpdate:()=>void,onState:(state:RuntimeConnectionState)=>void){
 let socket:WebSocket|null=null,timer:ReturnType<typeof setTimeout>|null=null,retries=0,stopped=false;
 const connect=()=>{if(stopped)return;onState(retries?"RECONNECTING":"CONNECTING");socket=new WebSocket(url);socket.onopen=()=>{retries=0;onState("CONNECTED")};socket.onmessage=()=>onUpdate();socket.onerror=()=>socket?.close();socket.onclose=()=>{if(stopped){onState("DISCONNECTED");return}onState("RECONNECTING");const delay=Math.min(1000*2**retries,15000);retries+=1;timer=setTimeout(connect,delay)}};
 connect();return()=>{stopped=true;if(timer)clearTimeout(timer);socket?.close()};
}
