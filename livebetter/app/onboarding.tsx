import React,{useState} from 'react';
import {t} from '../src/i18n';
import {Alert,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../src/context';
import {usePattern} from '../src/pattern';
import {Btn,Card,ChoiceChips,Field,Label,Note,Page,readError} from '../src/ui';
import {C,S} from '../src/theme';

const steps=['Household','Daily life','Priorities','Review'];
const titles=['First, your household','Tell us about daily life','Set your household priorities','Review your answers'];

export default function Onboarding(){
  const {onboard,state,demo}=useApp();
  const h=state.household;
  const guard=usePattern();          // changing an existing household needs the security pattern
  const [step,setStep]=useState(0);
  const [name,setName]=useState(h?.name||'My household');
  const [members,setMembers]=useState(String(h?.members||4));
  const [type,setType]=useState(h?.home_type||'House');
  const [water,setWater]=useState(h?.water_tariff||'Domestic');
  const [electricity,setElectricity]=useState(h?.electricity_tariff||'Domestic');
  const [budget,setBudget]=useState(String(h?.monthly_target||15000));
  const [diet,setDiet]=useState(h?.diet||'No preference');
  const [allergies,setAllergies]=useState(h?.allergies||'');
  const [waterHabit,setWaterHabit]=useState(h?.water_habit||'');
  const [appliances,setAppliances]=useState(h?.appliance_notes||'');

  function next(){
    if(step===0&&(!name.trim()||!Number.isInteger(Number(members))||Number(members)<1))
      return Alert.alert(t('Check your household'),t('Enter a name and a whole number of household members.'));
    if(step<steps.length-1)setStep(step+1);
    else void save();
  }
  async function save(){
    const target=Number(budget);
    if(!Number.isFinite(target)||target<0||!water.trim()||!electricity.trim())
      return Alert.alert(t('Check your priorities'),t('Enter a valid monthly target and both tariff categories.'));
    const send=async(stepUp?:string)=>{
      try{
        await onboard({name:name.trim(),members:Number(members),home_type:type,water_tariff:water,
          electricity_tariff:electricity,monthly_target:target,diet,allergies,water_habit:waterHabit,appliance_notes:appliances},stepUp);
        router.replace('/(tabs)/home');
      }catch(error){Alert.alert(t('Could not save household'),readError(error));}
    };
    if(h&&!demo)guard.ask('edit_household',send); else await send();
  }

  return <Page showTabs={false} back title={titles[step]}
    subtitle={t('A few quick answers help make your household picture more useful.')}>
    {guard.prompt}
    <View style={{gap:8}}>
      <View style={S.between}><Text style={S.muted}>STEP {step+1} OF {steps.length}</Text><Text style={S.muted}>{steps[step]}</Text></View>
      <View style={S.progressTrack}><View style={[S.progressFill,{width:`${((step+1)/steps.length)*100}%`}]}/></View>
    </View>

    {step===0?<Card>
      <Label>{t('About your home')}</Label>
      <Field label={t('Household name')} value={name} onChangeText={setName} placeholder={t('e.g. Our home')}/>
      <Field label={t('How many people live here?')} value={members} onChangeText={setMembers} keyboardType="number-pad"/>
      <ChoiceChips label={t('What type of home do you live in?')} options={['House','Apartment','Shared home','Other']}
        value={type} onChange={setType}/>
      <Note>{t('Only share details you are comfortable storing with the app.')}</Note>
    </Card>:null}

    {step===1?<Card>
      <Label>{t('Your daily life')}</Label>
      <Note>{t('These optional details help explain household patterns. You can skip them.')}</Note>
      <Field label={t('Water habits')} value={waterHabit} onChangeText={setWaterHabit}
        placeholder={t('e.g. Showers, laundry, garden watering')} multiline/>
      <Field label={t('Major appliances and usage')} value={appliances} onChangeText={setAppliances}
        placeholder={t('e.g. Air conditioner, washing machine')} multiline/>
    </Card>:null}

    {step===2?<Card>
      <Label>What matters to your household?</Label>
      <Field label={t('Monthly expense target (MUR)')} value={budget} onChangeText={setBudget} keyboardType="decimal-pad"/>
      <ChoiceChips label={t('Dietary preference')} options={['No preference','Vegetarian','Vegan','Other']}
        value={diet} onChange={setDiet}/>
      <Field label={t('Allergies or ingredients to avoid (optional)')} value={allergies}
        onChangeText={setAllergies} placeholder={t('Add any ingredients')}/>
      <Field label={t('Water tariff class')} value={water} onChangeText={setWater}/>
      <Field label={t('Electricity tariff class')} value={electricity} onChangeText={setElectricity}/>
      <Note>{t('Tariff categories are household notes, not a verified tariff calculation.')}</Note>
    </Card>:null}

    {step===3?<Card>
      <Label>{t('Your household is ready')}</Label>
      <Note>{t('Review these details before building your baseline. You can edit them later.')}</Note>
      <Summary label={t('Household')} value={`${members} people · ${type}`}/>
      <Summary label={t('Daily life')} value={waterHabit||appliances?t('Your household habits are saved'):t('No optional habits added')}/>
      <Summary label={t('Monthly target')} value={`MUR ${Number(budget||0).toLocaleString('en-MU')}`}/>
      <Summary label={t('Food preference')} value={diet}/>
      <Summary label={t('Water tariff note')} value={water}/>
      <Summary label={t('Electricity tariff note')} value={electricity}/>
      <View style={{backgroundColor:C.blue,borderRadius:13,padding:12}}>
        <Note>{t('Forecasts still need real bills. These answers do not measure current utility use or verify tariff rates.')}</Note>
      </View>
      <Btn title={t('Edit answers')} outline onPress={()=>setStep(0)}/>
    </Card>:null}

    <View style={S.row}>
      {step>0?<View style={{flex:1}}><Btn title={t('Back')} outline onPress={()=>setStep(step-1)}/></View>:null}
      <View style={{flex:1}}><Btn title={step===steps.length-1?t('Enter dashboard'):t('Continue  →')} onPress={next}/></View>
    </View>
  </Page>;
}

function Summary({label,value}:{label:string;value:string}){
  return <View style={{gap:3,paddingVertical:9,borderBottomWidth:1,borderBottomColor:C.line}}>
    <Text style={S.muted}>{label}</Text><Text style={S.body}>{value}</Text>
  </View>;
}
