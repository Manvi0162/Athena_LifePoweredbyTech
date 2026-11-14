// React Native Web has no Alert.alert (it does nothing), so on web every message the app shows with
// Alert.alert (e.g. "Password too short") was silently lost. Show it with the browser dialog instead.
import {Alert,Platform} from 'react-native';
if(Platform.OS==='web'&&typeof window!=='undefined'){
  Alert.alert=(title:string,message?:string)=>{window.alert(message?`${title}\n\n${message}`:title);};
}
