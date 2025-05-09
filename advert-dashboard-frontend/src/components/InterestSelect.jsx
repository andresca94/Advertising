import { useState, useRef, useEffect } from "react";

export default function InterestSelect({ options, selected, onChange }) {
  const [open, setOpen] = useState(false);
  const boxRef = useRef(null);

  /* cerrar al click fuera */
  useEffect(() => {
    const h = (e) => { if(boxRef.current && !boxRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const toggle = (opt) => {
    const next = selected.includes(opt)
      ? selected.filter(o => o!==opt)
      : [...selected, opt];
    onChange(next);
  };

  const remove = (opt,e)=>{
    e.stopPropagation();
    onChange(selected.filter(o=>o!==opt));
  };

  return (
    <div style={{position:"relative"}} ref={boxRef}>
      <div className="is-box" onClick={()=>setOpen(!open)}>
        {selected.length===0 &&
          <span className="placeholder">Select…</span>}
        {selected.map(opt=>(
          <span key={opt} className="chip">
            {opt}
            <button onClick={(e)=>remove(opt,e)}>&times;</button>
          </span>
        ))}
        <span style={{marginLeft:"auto",fontSize:12}}>{open?"▲":"▼"}</span>
      </div>

      {open && (
        <ul className="dropdown">
          {options.map(opt=>(
            <li key={opt} onClick={()=>toggle(opt)}>
              {selected.includes(opt)?"☑︎":"☐"} {opt}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
