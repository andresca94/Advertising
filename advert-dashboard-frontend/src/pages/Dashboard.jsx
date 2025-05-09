/**
 * Dashboard.jsx – Advertising Dashboard (compact “+” add-interest)
 */

import { useState, useEffect, useRef } from "react";
import api from "../services/axios";
import ModalView from "../components/ModalView";

export default function Dashboard() {
  /* ───────── constants ───────── */
  const AGE_MIN = 3;
  const AGE_MAX = 100;

  /* ───────── state ───────── */
  const emptyForm = {
    name: "",
    prompt: "",
    ageMin: 18,
    ageMax: 65,
    location: "",
    imageUrl: "",
    imageFile: null,
    useReference: false,
    derivePrompt: false,
    interests: [],
  };

  const [form,      setForm]      = useState(emptyForm);
  const [campaigns, setCampaigns] = useState([]);
  const [loading,   setLoading]   = useState(false);
  const [modalData, setModalData] = useState(null);

  /* dynamic interest list */
  const [options,   setOptions]   = useState([
    "Sports","Gaming","Fashion","Tech","Travel","Music",
  ]);

  /* ───────── fetch campaigns ───────── */
  useEffect(() => { api.get("/campaigns").then(r=>setCampaigns(r.data)); }, []);

  /* ───────── handlers ───────── */
  const onInput = e => setForm({ ...form, [e.target.name]: e.target.value });
  const onFile  = e => setForm({ ...form, imageFile: e.target.files[0] });

  const toggleInterest = label =>
    setForm(p => ({
      ...p,
      interests: p.interests.includes(label)
        ? p.interests.filter(i => i !== label)
        : [...p.interests, label],
    }));

  /* ➊ compact “+” chip -> prompt */
  const handleAddInterest = () => {
    const label = prompt("New interest:")?.trim();
    if (!label) return;
    if (!options.includes(label)) setOptions(o => [...o, label]);
    setForm(p => ({
      ...p,
      interests: p.interests.includes(label)
        ? p.interests
        : [...p.interests, label],
    }));
  };

  /* dual-range slider */
  const trackRef=useRef(null);
  const syncTrack=(l,r)=>{
    if(!trackRef.current) return;
    const range=AGE_MAX-AGE_MIN;
    trackRef.current.style.left =`${((l-AGE_MIN)/range)*100}%`;
    trackRef.current.style.right=`${100-((r-AGE_MIN)/range)*100}%`;
  };
  useEffect(()=>syncTrack(form.ageMin,form.ageMax),[]);
  const onAgeMin=e=>{
    let v=+e.target.value;
    if(v>form.ageMax-1)v=form.ageMax-1;
    setForm(p=>{const n={...p,ageMin:v};syncTrack(v,n.ageMax);return n;});
  };
  const onAgeMax=e=>{
    let v=+e.target.value;
    if(v<form.ageMin+1)v=form.ageMin+1;
    setForm(p=>{const n={...p,ageMax:v};syncTrack(n.ageMin,v);return n;});
  };

  /* upload helper */
  const uploadRef=async()=>{
    if(!(form.useReference||form.derivePrompt))return null;
    if(form.imageFile){
      const fd=new FormData();fd.append("file",form.imageFile);
      const{data}=await api.post("/upload_reference",fd);return data.filename;
    }
    if(form.imageUrl.trim()){
      const{data}=await api.post("/upload_reference_url",null,
        {params:{url:form.imageUrl.trim()}});return data.filename;
    }
    return null;
  };

  /* submit */
  const submit=async e=>{
    e.preventDefault();setLoading(true);
    try{
      const ref=await uploadRef();
      const payload={
        name:form.name,prompt:form.prompt,
        use_reference:form.useReference,
        derive_prompt_from_reference:form.derivePrompt,
        reference_filename:ref,
        targeting:{
          age_min:form.ageMin,age_max:form.ageMax,
          location:form.location,interests:form.interests,
        },
      };
      const{data}=await api.post("/campaigns",payload);
      setCampaigns([data,...campaigns]);
      setForm(emptyForm);syncTrack(emptyForm.ageMin,emptyForm.ageMax);
    }catch(err){console.error(err);}
    finally{setLoading(false);}
  };

  /* ───────── UI ───────── */
  return (
    <>
      {loading && (
        <div className="loader-wrap">
          <div className="spinner"></div>
          <p className="loader-msg">🚀 Generating your campaign… please wait ✨</p>
        </div>
      )}

      <ModalView data={modalData} onClose={()=>setModalData(null)} />

      <div className="min-h-screen flex flex-col">
        <header>
          <div className="bar">
            <h1>Ad Dashboard</h1>
            <button className="logout-btn"
              onClick={()=>{localStorage.removeItem("token");location.reload();}}>
              Logout
            </button>
          </div>
        </header>

        <main className="center">
          <div className="slide">
            {/* form */}
            <section style={{marginBottom:40}}>
              <h2 className="title">Create Campaign</h2>

              <form onSubmit={submit} className="form-grid">
                <div className="form-group full">
                  <label>Campaign Name</label>
                  <input name="name" value={form.name} onChange={onInput} required/>
                </div>

                <div className="form-group full">
                  <label>Prompt / Tagline</label>
                  <textarea name="prompt" rows={3} style={{resize:"vertical"}}
                    placeholder="Describe your ad creative…" value={form.prompt}
                    onChange={onInput} required/>
                </div>

                {/* age slider */}
                <div className="form-group full">
                  <label>Age Range: {form.ageMin} – {form.ageMax}</label>
                  <div className="range-container">
                    <input type="range" min={AGE_MIN} max={AGE_MAX}
                           value={form.ageMin} onChange={onAgeMin}
                           className="thumb thumb--left"/>
                    <input type="range" min={AGE_MIN} max={AGE_MAX}
                           value={form.ageMax} onChange={onAgeMax}
                           className="thumb thumb--right"/>
                    <div className="range-slider__track"/>
                    <div className="range-slider__range" ref={trackRef}/>
                  </div>
                </div>

                <div className="form-group">
                  <label>Location</label>
                  <input name="location" value={form.location}
                         onChange={onInput} placeholder="Location"/>
                </div>

                {/* toggles */}
                <div className="form-group toggle-row full">
                  <label className="switch">
                    <input type="checkbox" checked={form.useReference}
                      onChange={e=>setForm({...form,useReference:e.target.checked,derivePrompt:false})}/>
                    <span className="slider"/>
                  </label>
                  <span className="toggle-label">Use uploaded / linked image</span>
                </div>

                <div className="form-group toggle-row full">
                  <label className="switch">
                    <input type="checkbox" checked={form.derivePrompt}
                      onChange={e=>setForm({...form,derivePrompt:e.target.checked,useReference:false})}/>
                    <span className="slider"/>
                  </label>
                  <span className="toggle-label">Use image only for inspiration</span>
                </div>

                <div className="form-group">
                  <label>Image URL (optional)</label>
                  <input name="imageUrl" value={form.imageUrl}
                         onChange={onInput} placeholder="https://…"
                         disabled={!(form.useReference||form.derivePrompt)}/>
                </div>
                <div className="form-group">
                  <label>Upload Image</label>
                  <input type="file" accept="image/*" onChange={onFile}
                         disabled={!(form.useReference||form.derivePrompt)}/>
                </div>

                {/* interests with compact + */}
                <div className="form-group full">
                  <label>Interests</label>
                  <div className="chip-wrapper">
                    {options.map(l=>(
                      <label key={l}
                             className={`chip ${form.interests.includes(l)?"chip--active":""}`}>
                        <input type="checkbox" style={{display:"none"}}
                               checked={form.interests.includes(l)}
                               onChange={()=>toggleInterest(l)}/>
                        {l}
                      </label>
                    ))}
                    {/* + chip */}
                    <div className="chip chip--add" title="Add interest" onClick={handleAddInterest}>+</div>
                  </div>
                </div>

                <button className="btn full">Create Campaign</button>
              </form>
            </section>

            {/* list */}
            <section>
              <div className="flex-between">
                <h2 className="title">Campaigns</h2>
                <button className="link"
                  onClick={()=>api.get("/campaigns").then(r=>setCampaigns(r.data))}>
                  Refresh
                </button>
              </div>

              {campaigns.length===0 ? (
                <p className="text-muted">No campaigns yet.</p>
              ) : (
                <div className="grid-campaign">
                  {campaigns.map(c=>(
                    <div key={c.id} className="card">
                      <button className="enlarge-btn" onClick={()=>setModalData(c)}>⤢</button>
                      <h3>{c.name}</h3>
                      <span className="badge">{c.status}</span>
                      <p className="text-small">
                        <strong>CTR:</strong> {c.ctr}% | <strong>Impr.:</strong> {c.impressions}
                      </p>
                      <p className="quote">“{c.ad_copy}”</p>
                      <img className="banner-img" alt="banner"
                           src={`${import.meta.env.VITE_API_URL}/static/generated/${c.generated_filename}`}/>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        </main>
      </div>

      {/* ───────── styles ───────── */}
      <style>{`
        /* dual-range slider */
        .range-container{position:relative;height:40px}
        .range-container input[type=range]{pointer-events:none;position:absolute;left:0;top:0;width:100%;height:40px;background:none;margin:0;-webkit-appearance:none;}
        .range-container input[type=range]::-webkit-slider-thumb{pointer-events:all;width:18px;height:18px;border-radius:50%;background:#4f46e5;border:none;-webkit-appearance:none;}
        .range-container input[type=range]::-moz-range-thumb{pointer-events:all;width:18px;height:18px;border-radius:50%;background:#4f46e5;border:none;}
        .thumb--left{z-index:3}.thumb--right{z-index:4}
        .range-slider__track,.range-slider__range{position:absolute;left:0;right:0;top:50%;height:4px;transform:translateY(-50%);border-radius:4px;}
        .range-slider__track{background:#d1d5db;z-index:1}.range-slider__range{background:#4f46e5;z-index:2}

        /* chips */
        .chip-wrapper{display:flex;flex-wrap:wrap;gap:8px}
        .chip{padding:6px 12px;border-radius:16px;font-size:.9rem;background:#f3f4f6;border:1px solid #d1d5db;cursor:pointer;user-select:none}
        .chip--active{background:#e0e7ff;border-color:#4f46e5}
        .chip--add{font-weight:700;background:#eef2ff;border-color:#c7d2fe;}

        /* basic */
        .title{font-size:20px;font-weight:600}
        .form-grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
        .form-group{display:flex;flex-direction:column}.form-group.full{grid-column:span 2}
        .form-group label{font-weight:500;margin-bottom:4px}
        .form-group input[type=text],.form-group input[type=url],.form-group input[type=file],.form-group textarea{padding:10px;border:1px solid #cbd5e1;border-radius:4px;font-size:.95rem;}
        .form-group textarea{min-height:80px}
        .toggle-row{flex-direction:row;align-items:center}.toggle-label{margin-left:8px}
        .switch{position:relative;display:inline-block;width:40px;height:20px}.switch input{opacity:0;width:0;height:0}
        .slider{position:absolute;inset:0;background:#ccc;border-radius:20px;transition:.2s}
        .slider::before{content:"";position:absolute;top:2px;left:3px;width:15px;height:15px;background:#fff;border-radius:50%;transition:.2s}
        .switch input:checked + .slider{background:#4f46e5}.switch input:checked + .slider::before{transform:translateX(20px)}
        .btn{background:#4f46e5;color:#fff;padding:12px;border:none;border-radius:4px;cursor:pointer;font-weight:600}.btn.full{grid-column:span 2}
        .btn:hover{background:#4338ca}
        .flex-between{display:flex;justify-content:space-between;align-items:center}
        .link{background:none;border:none;color:#4f46e5;cursor:pointer}
        .loader-wrap{position:fixed;inset:0;background:rgba(255,255,255,.8);display:flex;flex-direction:column;justify-content:center;align-items:center;z-index:100}
        .spinner{width:48px;height:48px;border:6px solid #e5e7eb;border-top-color:#4f46e5;border-radius:50%;animation:spin .8s linear infinite}
        @keyframes spin{to{transform:rotate(360deg)}}
        .loader-msg{margin-top:12px;font-weight:500;color:#4f46e5}
        .grid-campaign{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
        .card{position:relative;padding:12px;border:1px solid #e5e7eb;border-radius:8px;background:#fff}
        .banner-img{width:100%;height:120px;object-fit:cover;border-radius:8px;margin-top:6px}
        .text-small{font-size:14px;color:#374151}.quote{font-size:14px;font-style:italic;color:#1f2937;margin-top:6px}
      `}</style>
    </>
  );
}
