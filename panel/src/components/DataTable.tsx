import { useTable, flexRender, type ColumnDef } from '@tanstack/react-table';
export default function DataTable({data,columns}:{data:Record<string,unknown>[];columns:ColumnDef<{},Record<string,unknown>>[]}){
 const table=useTable({features:{},data,columns});
 return <div className="table-scroll"><table><thead>{table.getHeaderGroups().map(group=><tr key={group.id}>{group.headers.map(header=><th key={header.id}>{flexRender(header.column.columnDef.header,header.getContext())}</th>)}</tr>)}</thead><tbody>{table.getRowModel().rows.map(row=><tr key={row.id}>{row.getAllCells().map(cell=><td key={cell.id}>{flexRender(cell.column.columnDef.cell??(()=>String(cell.getValue()??'—')),cell.getContext())}</td>)}</tr>)}</tbody></table>{!data.length&&<p className="empty">No hay registros en este periodo.</p>}</div>;
}
