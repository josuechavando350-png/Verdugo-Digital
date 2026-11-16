import { useEffect, useRef } from 'react';
import { init, use } from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent, AriaComponent } from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';
import type { AdsReport } from '../lib/api';
use([LineChart,GridComponent,TooltipComponent,LegendComponent,AriaComponent,SVGRenderer]);
export function chartOptions(daily:AdsReport['daily']){return {animation:false,aria:{enabled:true},color:['#153e39','#b58527'],legend:{bottom:0,data:['Gasto','Conversiones']},tooltip:{trigger:'axis'},grid:{left:55,right:35,top:25,bottom:60},xAxis:{type:'category',data:daily.map(d=>d.day.slice(5)),axisLine:{lineStyle:{color:'#d5d8d4'}}},yAxis:[{type:'value',splitLine:{lineStyle:{color:'#e9ebe7'}}},{type:'value',splitLine:{show:false}}],series:[{name:'Gasto',type:'line',data:daily.map(d=>d.spend),smooth:false,areaStyle:{opacity:0.05}},{name:'Conversiones',type:'line',yAxisIndex:1,data:daily.map(d=>d.platform_conversions)}]};}
export default function Chart({daily}:{daily:AdsReport['daily']}){
 const element=useRef<HTMLDivElement>(null);
 useEffect(()=>{if(!element.current)return;const chart=init(element.current,undefined,{renderer:'svg'});chart.setOption(chartOptions(daily));const resize=()=>chart.resize();window.addEventListener('resize',resize);return()=>{window.removeEventListener('resize',resize);chart.dispose();};},[daily]);
 return <div ref={element} className="chart" role="img" aria-label="Gasto y conversiones diarias. Los valores también están disponibles en el reporte descargable."/>;
}
