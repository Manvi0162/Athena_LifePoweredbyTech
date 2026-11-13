import React,{useMemo,useState} from 'react';
import {Alert,Platform,Pressable,ScrollView,Text,View} from 'react-native';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import {useApp} from '../../src/context';
import {Activity as ActivityEntry} from '../../src/types';
import {C,S} from '../../src/theme';
import {Card,Label,Note,Page} from '../../src/ui';

type ActivityFilter='All'|'Bills'|'Pantry'|'Goals';
const filters:ActivityFilter[]=['All','Bills','Pantry','Goals'];
const months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const fullMonths=['January','February','March','April','May','June','July','August','September','October','November','December'];
const weekdays=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];

function toIsoDate(date:Date){
  return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
}

function toDisplayDate(iso:string){
  const [year,month,day]=iso.split('-').map(Number);
  return `${String(day).padStart(2,'0')} ${months[month-1]} ${year}`;
}

function parseDisplayDate(value:string):string|null{
  const match=/^(\d{2}) ([A-Za-z]{3}) (\d{4})$/.exec(value.trim());
  if(!match)return null;
  const day=Number(match[1]);
  const month=months.findIndex(item=>item.toLowerCase()===match[2].toLowerCase());
  const year=Number(match[3]);
  if(month<0)return null;
  const date=new Date(year,month,day,12);
  if(date.getFullYear()!==year||date.getMonth()!==month||date.getDate()!==day)return null;
  return `${year}-${String(month+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
}

function escapeHtml(value:string){
  return value.replace(/[&<>"']/g,char=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
  })[char]||char);
}

function makeReportHtml(entries:ActivityEntry[],start:string,end:string,filter:ActivityFilter){
  const rows=entries.map(entry=>`<tr>
    <td>${escapeHtml(new Date(entry.at).toLocaleString())}</td>
    <td>${escapeHtml(entry.kind.toUpperCase())}</td>
    <td>${escapeHtml(entry.message)}</td>
  </tr>`).join('');
  return `<!doctype html><html><head><meta charset="utf-8"><title>Household activity</title>
    <style>
      body{font-family:Arial,sans-serif;color:#0B2433;margin:32px}
      h1{margin-bottom:6px}p{color:#526777}
      table{width:100%;border-collapse:collapse;margin-top:24px}
      th,td{text-align:left;padding:10px;border-bottom:1px solid #DCE8EB;vertical-align:top}
      th{background:#EAF4F8}
    </style></head><body>
    <h1>Household activity</h1>
    <p>${escapeHtml(filter)} · ${escapeHtml(toDisplayDate(start))} to ${escapeHtml(toDisplayDate(end))}</p>
    <table><thead><tr><th>Date and time</th><th>Activity</th><th>Details</th></tr></thead>
    <tbody>${rows||'<tr><td colspan="3">No activity was recorded for this period.</td></tr>'}</tbody></table>
    </body></html>`;
}

function matchesFilter(entry:ActivityEntry,filter:ActivityFilter){
  const kind=entry.kind.toLowerCase();
  if(filter==='All')return true;
  if(filter==='Bills')return kind==='bill'||kind==='bills';
  if(filter==='Pantry')return ['receipt','cook','pantry'].includes(kind);
  return kind==='goal'||kind==='goals';
}

function groupLabel(isoDate:string,today:string){
  const [year,month,day]=isoDate.split('-').map(Number);
  const date=new Date(year,month-1,day,12);
  const previous=new Date();
  previous.setDate(previous.getDate()-1);
  const yesterday=toIsoDate(previous);
  const dateLabel=`${String(day).padStart(2,'0')} ${months[month-1]}`.toUpperCase();
  if(isoDate===today)return `TODAY · ${dateLabel}`;
  if(isoDate===yesterday)return `YESTERDAY · ${dateLabel}`;
  return `${date.toLocaleDateString(undefined,{weekday:'long'}).toUpperCase()} · ${dateLabel}`;
}

function activityPresentation(entry:ActivityEntry){
  const kind=entry.kind.toLowerCase();
  if(kind==='bill'){
    const utility=entry.message.toLowerCase().includes('electricity')?'Electricity':'Water';
    const units=entry.message.match(/\(([^)]+)\)/)?.[1];
    return {title:`${utility} bill added`,detail:units?`${units} · Historical baseline updated`:entry.message,icon:'▤'};
  }
  if(kind==='receipt'){
    const receipt=entry.message.match(/(\d+) items?,\s*Rs\s*([\d,.]+)/i);
    const detail=receipt?`${receipt[1]} products · Rs ${Number(receipt[2].replace(/,/g,'')).toLocaleString('en-MU',{maximumFractionDigits:0})} purchase saved`:entry.message;
    return {title:'Grocery receipt confirmed',detail,icon:'▧'};
  }
  if(kind==='cook'){
    const recipe=entry.message.match(/^Cooked ([^;]+)/i)?.[1];
    return {title:recipe?`${recipe} cooked`:'Meal cooked',detail:'Pantry quantities adjusted once',icon:'✓'};
  }
  if(kind==='goal'||kind==='goals')return {title:'Household goals set',detail:entry.message,icon:'◎'};
  if(kind==='household')return {title:'Household details updated',detail:entry.message,icon:'⌂'};
  return {title:'Pantry updated',detail:entry.message,icon:'▤'};
}

export default function Activity(){
  const {state}=useApp();
  const today=toIsoDate(new Date());
  const firstDay=`${today.slice(0,7)}-01`;
  const [filter,setFilter]=useState<ActivityFilter>('All');
  const [draftStart,setDraftStart]=useState(toDisplayDate(firstDay));
  const [draftEnd,setDraftEnd]=useState(toDisplayDate(today));
  const [appliedStart,setAppliedStart]=useState(firstDay);
  const [appliedEnd,setAppliedEnd]=useState(today);
  const [rangeError,setRangeError]=useState<string|null>(null);
  const [exporting,setExporting]=useState(false);
  const [calendarTarget,setCalendarTarget]=useState<'start'|'end'|null>(null);
  const [calendarMode,setCalendarMode]=useState<'days'|'months'|'years'>('days');
  const [calendarMonth,setCalendarMonth]=useState(()=>new Date(new Date().getFullYear(),new Date().getMonth(),1));
  const currentMonth=new Date(new Date().getFullYear(),new Date().getMonth(),1);
  const calendarIsCurrentMonth=calendarMonth.getFullYear()===currentMonth.getFullYear()
    &&calendarMonth.getMonth()===currentMonth.getMonth();
  const calendarYears=Array.from({length:31},(_,index)=>currentMonth.getFullYear()-index);
  const calendarOffset=(calendarMonth.getDay()+6)%7;
  const calendarDays=Array.from({length:new Date(calendarMonth.getFullYear(),calendarMonth.getMonth()+1,0).getDate()},
    (_,index)=>new Date(calendarMonth.getFullYear(),calendarMonth.getMonth(),index+1));
  const calendarCells: (Date|null)[]=[
    ...Array.from({length:calendarOffset},()=>null),
    ...calendarDays,
  ];
  while(calendarCells.length%7)calendarCells.push(null);

  const filtered=useMemo(()=>state.activity.filter(item=>{
    const date=new Date(item.at);
    if(!Number.isFinite(date.getTime()))return false;
    const day=toIsoDate(date);
    return day>=appliedStart&&day<=appliedEnd&&matchesFilter(item,filter);
  }).sort((a,b)=>b.at.localeCompare(a.at)),[state.activity,appliedStart,appliedEnd,filter]);

  const groups=useMemo(()=>{
    const result:{date:string;label:string;entries:ActivityEntry[]}[]=[];
    for(const entry of filtered){
      const date=toIsoDate(new Date(entry.at));
      let group=result[result.length-1];
      if(!group||group.date!==date){
        group={date,label:groupLabel(date,today),entries:[]};
        result.push(group);
      }
      group.entries.push(entry);
    }
    return result;
  },[filtered,today]);

  function applyRange(){
    const start=parseDisplayDate(draftStart);
    const end=parseDisplayDate(draftEnd);
    if(!start||!end){
      setRangeError('Enter valid dates like 01 Nov 2026.');
      return false;
    }
    if(end>today){
      setRangeError('The end date cannot be later than today.');
      return false;
    }
    if(start>end){
      setRangeError('The start date must be on or before the end date.');
      return false;
    }
    setRangeError(null);
    setAppliedStart(start);
    setAppliedEnd(end);
    return true;
  }

  function openCalendar(target:'start'|'end'){
    const value=target==='start'?draftStart:draftEnd;
    const parsed=parseDisplayDate(value);
    const date=parsed?new Date(`${parsed}T12:00:00`):new Date();
    setCalendarMonth(new Date(date.getFullYear(),date.getMonth(),1));
    setCalendarMode('days');
    setCalendarTarget(target);
  }

  function selectCalendarDate(date:Date){
    if(toIsoDate(date)>today)return;
    const value=toDisplayDate(toIsoDate(date));
    if(calendarTarget==='start')setDraftStart(value);
    if(calendarTarget==='end')setDraftEnd(value);
    setRangeError(null);
    setCalendarTarget(null);
  }

  async function exportPdf(){
    if(!applyRange())return;
    setExporting(true);
    try{
      const start=parseDisplayDate(draftStart)!;
      const end=parseDisplayDate(draftEnd)!;
      const entries=state.activity.filter(item=>{
        const date=new Date(item.at);
        if(!Number.isFinite(date.getTime()))return false;
        const day=toIsoDate(date);
        return day>=start&&day<=end&&matchesFilter(item,filter);
      }).sort((a,b)=>b.at.localeCompare(a.at));
      const html=makeReportHtml(entries,start,end,filter);
      if(Platform.OS==='web'){
        await Print.printAsync({html});
      }else{
        const file=await Print.printToFileAsync({html});
        if(!await Sharing.isAvailableAsync())
          throw Error('PDF sharing is unavailable on this device.');
        await Sharing.shareAsync(file.uri,{mimeType:'application/pdf',dialogTitle:'Export household activity'});
      }
    }catch(error){
      Alert.alert('Could not export activity',error instanceof Error?error.message:String(error));
    }finally{
      setExporting(false);
    }
  }

  return <Page back hideBrand headerRight={<View style={S.activityHeaderRight}>
    <View style={S.activityAuditTag}><Text style={S.activityAuditTagText}>AUDIT TRAIL</Text></View>
  </View>} title="Household activity" subtitle="A clear record of purchases, corrections and actions.">

    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={S.activityFilterRow}>
      {filters.map(option=>{
        const selected=filter===option;
        return <Pressable key={option} accessibilityRole="button" accessibilityState={{selected}}
          onPress={()=>setFilter(option)} style={[S.activityFilter,selected&&S.activityFilterSelected]}>
          <Text style={[S.activityFilterText,selected&&S.activityFilterTextSelected]}>{option}</Text>
        </Pressable>;
      })}
    </ScrollView>

    <View style={[S.card,S.periodCard]}>
      <View style={S.periodHeader}>
        <View style={S.row}>
          <Text style={S.periodIcon}>▦</Text>
          <Label>Period</Label>
        </View>
        <Pressable accessibilityRole="button" disabled={exporting} onPress={()=>void exportPdf()}
          style={[S.exportButton,exporting&&{opacity:0.6}]}>
          <Text style={S.exportButtonText}>{exporting?'Preparing…':'⇩  Export PDF'}</Text>
        </Pressable>
      </View>
      <View style={S.periodControls}>
        <View style={S.periodDateField}>
          <Text style={S.periodDateLabel}>From</Text>
          <Pressable accessibilityRole="button" accessibilityLabel={`Choose start date, ${draftStart}`}
            accessibilityHint="Opens a calendar to choose the start date" accessibilityState={{expanded:calendarTarget==='start'}}
            onPress={()=>openCalendar('start')} style={S.periodDateInput}>
            <Text style={S.periodDateValue}>{draftStart}</Text>
            <Text style={S.calendarIcon}>▦</Text>
          </Pressable>
        </View>
        <View style={S.periodDateField}>
          <Text style={S.periodDateLabel}>To</Text>
          <Pressable accessibilityRole="button" accessibilityLabel={`Choose end date, ${draftEnd}`}
            accessibilityHint="Opens a calendar to choose the end date" accessibilityState={{expanded:calendarTarget==='end'}}
            onPress={()=>openCalendar('end')} style={S.periodDateInput}>
            <Text style={S.periodDateValue}>{draftEnd}</Text>
            <Text style={S.calendarIcon}>▦</Text>
          </Pressable>
        </View>
        <Pressable accessibilityRole="button" onPress={applyRange} style={S.applyButton}>
          <Text style={S.applyButtonText}>Apply</Text>
        </Pressable>
      </View>
      {calendarTarget?<View style={S.calendarPopup}>
        <View style={S.calendarHeader}>
          <View style={S.calendarTitleControls}>
            <Pressable accessibilityRole="button" accessibilityLabel="Choose month"
              accessibilityState={{expanded:calendarMode==='months'}} onPress={()=>setCalendarMode('months')}
              style={S.calendarTitleButton}>
              <Text style={S.calendarMonth}>{fullMonths[calendarMonth.getMonth()]}</Text>
              <Text style={S.calendarTitleChevron}>⌄</Text>
            </Pressable>
            <Pressable accessibilityRole="button" accessibilityLabel="Choose year"
              accessibilityState={{expanded:calendarMode==='years'}} onPress={()=>setCalendarMode('years')}
              style={S.calendarTitleButton}>
              <Text style={S.calendarMonth}>{calendarMonth.getFullYear()}</Text>
              <Text style={S.calendarTitleChevron}>⌄</Text>
            </Pressable>
          </View>
          <View style={S.calendarNavigation}>
            <Pressable accessibilityRole="button" accessibilityLabel="Previous month"
              onPress={()=>setCalendarMonth(current=>new Date(current.getFullYear(),current.getMonth()-1,1))}
              style={S.calendarNavButton}><Text style={S.calendarNavText}>‹</Text></Pressable>
            <Pressable accessibilityRole="button" accessibilityLabel="Next month" disabled={calendarIsCurrentMonth}
              onPress={()=>setCalendarMonth(current=>new Date(current.getFullYear(),current.getMonth()+1,1))}
              style={[S.calendarNavButton,calendarIsCurrentMonth&&S.calendarNavButtonDisabled]}>
              <Text style={[S.calendarNavText,calendarIsCurrentMonth&&S.calendarNavTextDisabled]}>›</Text>
            </Pressable>
            <Pressable accessibilityRole="button" accessibilityLabel="Close calendar"
              onPress={()=>setCalendarTarget(null)} style={S.calendarCloseButton}>
              <Text style={S.calendarCloseText}>Close</Text>
            </Pressable>
          </View>
        </View>
        {calendarMode==='days'?<View style={S.calendarGrid}>
            {weekdays.map(day=><View key={day} style={S.calendarCell}>
              <Text style={S.calendarWeekday}>{day}</Text>
            </View>)}
            {calendarCells.map((date,index)=>{
              if(!date)return <View key={`empty-${index}`} style={S.calendarCell}/>;
              const iso=toIsoDate(date);
              const selected=iso===parseDisplayDate(calendarTarget==='start'?draftStart:draftEnd);
              const currentDay=iso===today;
              const future=iso>today;
              return <Pressable key={iso} accessibilityRole="button" disabled={future}
                accessibilityLabel={`Select ${date.toLocaleDateString(undefined,{day:'numeric',month:'long',year:'numeric'})}${future?', unavailable':''}`}
                accessibilityState={{selected,disabled:future}} onPress={()=>selectCalendarDate(date)}
                style={[S.calendarCell,S.calendarDay,selected&&S.calendarDaySelected,currentDay&&!selected&&S.calendarDayToday,future&&S.calendarDayDisabled]}>
                <Text style={[S.calendarDayText,selected&&S.calendarDayTextSelected,future&&S.calendarDayTextDisabled]}>{date.getDate()}</Text>
              </Pressable>;
            })}
          </View>:<View style={S.calendarSelectGrid}>
            {calendarMode==='months'?fullMonths.map((month,index)=>{
              const selected=index===calendarMonth.getMonth();
              const futureMonth=calendarMonth.getFullYear()===currentMonth.getFullYear()&&index>currentMonth.getMonth();
              return <Pressable key={month} accessibilityRole="button" disabled={futureMonth}
                accessibilityState={{selected,disabled:futureMonth}}
                onPress={()=>{setCalendarMonth(current=>new Date(current.getFullYear(),index,1));setCalendarMode('days');}}
                style={[S.calendarSelectItem,selected&&S.calendarDaySelected,futureMonth&&S.calendarDayDisabled]}>
                <Text style={[S.calendarSelectText,selected&&S.calendarDayTextSelected,futureMonth&&S.calendarDayTextDisabled]}>{month.slice(0,3)}</Text>
              </Pressable>;
            }):calendarYears.map(year=>{
              const selected=year===calendarMonth.getFullYear();
              return <Pressable key={year} accessibilityRole="button" accessibilityState={{selected}}
                onPress={()=>{setCalendarMonth(current=>new Date(year,current.getMonth(),1));setCalendarMode('months');}}
                style={[S.calendarSelectItem,selected&&S.calendarDaySelected]}>
                <Text style={[S.calendarSelectText,selected&&S.calendarDayTextSelected]}>{year}</Text>
              </Pressable>;
            })}
          </View>}
      </View>:null}
      {rangeError?<Text style={S.error}>{rangeError}</Text>:null}
    </View>

    {groups.length?groups.map(group=><View key={group.date} style={S.activityGroup}>
      <Text style={S.activityGroupHeading}>{group.label}</Text>
      {group.entries.map((entry,index)=>{
        const presentation=activityPresentation(entry);
        return <View key={entry.id} style={S.timelineRow}>
          <View style={S.timelineRail}>
            <View style={S.timelineIcon}><Text style={S.timelineIconText}>{presentation.icon}</Text></View>
            {index<group.entries.length-1?<View style={S.timelineLine}/>:null}
          </View>
          <View style={[S.timelineContent,index<group.entries.length-1&&S.timelineContentDivider]}>
            <Text style={S.timelineTitle}>{presentation.title}</Text>
            <Text style={S.timelineDetail}>{presentation.detail}</Text>
            <Text style={S.timelineTime}>{new Date(entry.at).toLocaleTimeString(undefined,{hour:'2-digit',minute:'2-digit',hour12:false})}</Text>
          </View>
        </View>;
      })}
    </View>):<Card><Note>No activity was recorded for this category and period.</Note></Card>}
  </Page>;
}
