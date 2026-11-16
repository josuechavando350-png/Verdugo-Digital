import { onCLS, onINP, onLCP } from 'web-vitals';
export function watchPerformance(onMetric:(name:string,value:number)=>void){
  const local=({name,value}:{name:string;value:number})=>onMetric(name,Math.round(value*100)/100);
  onCLS(local);onINP(local);onLCP(local);
}
