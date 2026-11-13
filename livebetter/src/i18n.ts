// App language: English, French or Kreol Morisien. Chosen at registration (and in Settings), saved on the phone.
// t('English text') returns the translation, or the English text when a translation is missing.
// Numbers, dates and amounts calculated by the backend are never translated or changed.
import AsyncStorage from '@react-native-async-storage/async-storage';
import {FR,MFE} from './translations';

export type Lang='en'|'fr'|'mfe';
export const LANGS:{code:Lang;label:string}[]=[{code:'en',label:'English'},{code:'fr',label:'Français'},{code:'mfe',label:'Kreol Morisien'}];
const KEY='@livebetter-lang';
let current:Lang='en';
export const getLang=()=>current;
export async function loadLang(){try{const v=await AsyncStorage.getItem(KEY);if(v==='fr'||v==='mfe'||v==='en')current=v;}catch{}return current;}
export async function saveLang(l:Lang){current=l;try{await AsyncStorage.setItem(KEY,l);}catch{}}
export function t(s:string):string{
  if(current==='en')return s;
  const d=current==='fr'?FR:MFE;
  return d[s]??s;
}
