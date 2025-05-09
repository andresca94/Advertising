export default function ModalView({ data, onClose }) {
    if (!data) return null;
    return (
      <div className="modal" onClick={onClose}>
        <div className="modal-box" onClick={(e) => e.stopPropagation()}>
          <button className="close-btn" onClick={onClose}>✕</button>
          <img
            src={`${import.meta.env.VITE_API_URL}/static/generated/${data.generated_filename}`}
            alt="banner"
          />
          <h2 style={{ fontSize: 20, fontWeight: 600, marginTop: 12 }}>
            {data.name}
          </h2>
          <p style={{ fontStyle: "italic", margin: "8px 0" }}>“{data.ad_copy}”</p>
          <p><strong>Target:</strong> {data.targeting.age_min}-{data.targeting.age_max}, {data.targeting.location}</p>
          <p><strong>CTR:</strong> {data.ctr}% &nbsp; | &nbsp;
             <strong>Impr.:</strong> {data.impressions} &nbsp; | &nbsp;
             <strong>Clicks:</strong> {data.clicks}</p>
        </div>
      </div>
    );
  }
  