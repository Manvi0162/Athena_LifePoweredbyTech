import { StyleSheet } from 'react-native';
export const C = { bg:'#F5F8F7', ink:'#142D2A', muted:'#60716D', green:'#087F6C', mint:'#DBF3EA',
  white:'#FFFFFF', line:'#DDE8E3', blue:'#E3F2FB', amber:'#FFF1D8', red:'#9B3333', dangerBg:'#FFF0F0' };
export const S = StyleSheet.create({
  screen:{flex:1,backgroundColor:C.bg}, content:{padding:18,paddingBottom:32,gap:14},
  card:{backgroundColor:C.white,borderRadius:18,padding:16,borderWidth:1,borderColor:C.line,gap:9},
  h1:{fontSize:26,fontWeight:'800',color:C.ink}, h2:{fontSize:19,fontWeight:'800',color:C.ink},
  title:{fontSize:16,fontWeight:'700',color:C.ink}, body:{fontSize:14,lineHeight:21,color:C.ink},
  muted:{fontSize:12,lineHeight:18,color:C.muted}, amount:{fontSize:28,fontWeight:'800',color:C.green},
  row:{flexDirection:'row',alignItems:'center',gap:10}, between:{flexDirection:'row',justifyContent:'space-between',alignItems:'center'},
  field:{borderWidth:1,borderColor:C.line,borderRadius:12,paddingHorizontal:12,paddingVertical:11,color:C.ink,backgroundColor:C.white,marginTop:4},
  tag:{alignSelf:'flex-start',backgroundColor:C.mint,borderRadius:20,paddingHorizontal:10,paddingVertical:4},
  tagText:{fontSize:11,fontWeight:'700',color:C.green}, btn:{paddingVertical:13,paddingHorizontal:16,backgroundColor:C.green,borderRadius:13,alignItems:'center',justifyContent:'center'},
  btnText:{color:'white',fontWeight:'800',fontSize:14}, outline:{backgroundColor:C.white,borderColor:C.green,borderWidth:1},
  outlineText:{color:C.green}, divider:{height:1,backgroundColor:C.line,marginVertical:4},
  error:{backgroundColor:C.dangerBg,padding:12,borderRadius:10,color:C.red},
});
export const money = (n:number|null|undefined) => n==null ? 'Not available' : `Rs ${n.toLocaleString('en-MU',{maximumFractionDigits:2})}`;
