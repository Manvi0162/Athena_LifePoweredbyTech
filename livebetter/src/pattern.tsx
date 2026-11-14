// Security pattern (surprise card "Misuse"): a 3x3 grid of dots numbered 1-9.
// Drag across the dots (phone) or tap them one by one (web / accessibility), then confirm.
// The pattern is checked by the backend (core/security.py), never in the app: the app only receives a
// one-time permission for ONE action, valid 5 minutes, sent with that request as X-Step-Up.
import React,{useRef,useState} from 'react';
import {t} from './i18n';
import {GestureResponderEvent,LayoutChangeEvent,Modal,Pressable,Text,View} from 'react-native';
import {ApiError} from './api';
import {useApp} from './context';
import {SensitiveAction} from './types';
import {C,S} from './theme';
import {Btn,Note} from './ui';

const SIZE=240, CELL=SIZE/3, HIT=CELL*0.38;

export function PatternGrid({value,onChange,disabled}:{value:number[];onChange:(v:number[])=>void;disabled?:boolean}){
  const box=useRef({w:SIZE,h:SIZE});
  const current=useRef<number[]>(value);current.current=value;
  function dotAt(e:GestureResponderEvent){
    const {locationX:x,locationY:y}=e.nativeEvent;
    const cw=box.current.w/3, ch=box.current.h/3;
    const col=Math.floor(x/cw), row=Math.floor(y/ch);
    if(col<0||col>2||row<0||row>2)return null;
    const dx=x-(col+0.5)*cw, dy=y-(row+0.5)*ch;
    return Math.hypot(dx,dy)<=Math.max(HIT,Math.min(cw,ch)*0.42)?row*3+col+1:null;
  }
  function add(e:GestureResponderEvent){
    const d=dotAt(e);
    if(d&&!current.current.includes(d)){const next=[...current.current,d];current.current=next;onChange(next);}
  }
  const centre=(d:number)=>({x:((d-1)%3+0.5)*CELL,y:(Math.floor((d-1)/3)+0.5)*CELL});
  return <View accessibilityLabel={`Security pattern grid, ${value.length} dots selected`}
    style={{width:SIZE,height:SIZE,alignSelf:'center',borderRadius:22,backgroundColor:C.bg,opacity:disabled?0.5:1}}
    onLayout={(e:LayoutChangeEvent)=>{box.current={w:e.nativeEvent.layout.width,h:e.nativeEvent.layout.height};}}
    onStartShouldSetResponder={()=>!disabled} onMoveShouldSetResponder={()=>!disabled}
    onResponderGrant={add} onResponderMove={add}
    onResponderTerminationRequest={()=>false} onStartShouldSetResponderCapture={()=>!disabled} onMoveShouldSetResponderCapture={()=>!disabled}>
    {value.slice(1).map((d,i)=>{               // lines between consecutive dots
      const a=centre(value[i]),b=centre(d);
      const len=Math.hypot(b.x-a.x,b.y-a.y), ang=Math.atan2(b.y-a.y,b.x-a.x);
      return <View key={`l${i}`} pointerEvents="none" style={{position:'absolute',left:(a.x+b.x)/2-len/2,top:(a.y+b.y)/2-2,
        width:len,height:4,borderRadius:2,backgroundColor:C.green,opacity:0.55,transform:[{rotate:`${ang}rad`}]}}/>;
    })}
    {[1,2,3,4,5,6,7,8,9].map(d=>{
      const on=value.includes(d), p=centre(d);
      return <View key={d} pointerEvents="none" testID={`dot-${d}`} style={{position:'absolute',left:p.x-21,top:p.y-21,width:42,height:42,
        borderRadius:21,alignItems:'center',justifyContent:'center',backgroundColor:on?C.green:C.white,
        borderWidth:2,borderColor:on?C.green:C.line}}>
        <Text style={{fontSize:11,fontWeight:'800',color:on?C.white:C.muted}}>{on?value.indexOf(d)+1:''}</Text>
      </View>;
    })}
  </View>;
}

// Modal used before every protected action. onAllowed receives the one-time permission.
export function PatternPrompt({action,visible,onClose,onAllowed}:{action:SensitiveAction|null;visible:boolean;
  onClose:()=>void;onAllowed:(stepUp:string)=>void|Promise<void>}){
  const {verifyPattern}=useApp();
  const [dots,setDots]=useState<number[]>([]);
  const [message,setMessage]=useState<{text:string;bad:boolean}|null>(null);
  const [checking,setChecking]=useState(false);
  const labels:Record<SensitiveAction,string>={reset_account:'reset the account',restore_account:'restore your records',
    delete_bill:'delete a bill',edit_household:'change the household details',security_off:'switch security off'};
  function close(){setDots([]);setMessage(null);onClose();}
  async function check(){
    if(!action)return;
    if(dots.length<4){setMessage({text:t('Connect at least 4 dots.'),bad:true});return;}
    setChecking(true);
    try{
      const token=await verifyPattern(action,dots);
      setDots([]);setMessage(null);
      await onAllowed(token);
    }catch(e){
      setDots([]);
      if(e instanceof ApiError&&e.code==='pattern_required')
        setMessage({text:t('No security pattern is set yet. Set one in Settings → Security first.'),bad:true});
      else setMessage({text:e instanceof Error?e.message:String(e),bad:true});
    }finally{setChecking(false);}
  }
  return <Modal visible={visible} transparent animationType="fade" onRequestClose={close}>
    <View style={{flex:1,backgroundColor:'rgba(10,30,40,0.55)',justifyContent:'center',padding:18}}>
      <View style={[S.card,{gap:12}]}>
        <Text style={{fontSize:11,fontWeight:'800',letterSpacing:1,color:C.green}}>{t('PROTECTED ACTION')}</Text>
        <Text style={S.title}>Draw your security pattern to {action?labels[action]:'continue'}.</Text>
        <Note>This stops someone else using this phone (for example a child) from changing or wiping your household records.</Note>
        <PatternGrid value={dots} onChange={v=>{setDots(v);setMessage(null);}} disabled={checking}/>
        {message?<Text accessibilityLiveRegion="polite" style={{color:message.bad?C.red:C.green,fontWeight:'700'}}>{message.text}</Text>:null}
        <View style={S.row}>
          <View style={{flex:1}}><Btn title={t('Clear')} outline onPress={()=>{setDots([]);setMessage(null);}}/></View>
          <View style={{flex:1}}><Btn title={checking?t('Checking…'):t('Confirm')} disabled={checking} onPress={()=>void check()}/></View>
        </View>
        <Pressable accessibilityRole="button" onPress={close} style={{alignSelf:'center',padding:6}}>
          <Text style={[S.muted,{fontWeight:'700'}]}>{t('Cancel')}</Text>
        </Pressable>
      </View>
    </View>
  </Modal>;
}

// Hook: const guard=usePattern(); guard.ask('delete_bill', async token=>{...}); render {guard.prompt}
export function usePattern(){
  const [action,setAction]=useState<SensitiveAction|null>(null);
  const pending=useRef<((t:string)=>void|Promise<void>)|null>(null);
  const ask=(a:SensitiveAction,fn:(stepUp:string)=>void|Promise<void>)=>{pending.current=fn;setAction(a);};
  const prompt=<PatternPrompt action={action} visible={!!action} onClose={()=>setAction(null)}
    onAllowed={async tok=>{const fn=pending.current;setAction(null);if(fn)await fn(tok);}}/>;
  return {ask,prompt};
}
