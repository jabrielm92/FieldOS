import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { publicAPI } from "@/lib/api";

function formatTime(isoString) {
  if (!isoString) return null;
  try {
    return new Date(isoString).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } catch {
    return null;
  }
}

function StatusBadge({ status }) {
  const map = {
    EN_ROUTE: { label: "On the way", color: "bg-blue-500" },
    IN_PROGRESS: { label: "Arrived", color: "bg-green-500" },
    COMPLETED: { label: "Completed", color: "bg-gray-500" },
  };
  const s = map[status] || { label: status, color: "bg-gray-500" };
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-white text-sm font-medium ${s.color}`}>
      <span className="w-2 h-2 rounded-full bg-white/80 inline-block" />
      {s.label}
    </span>
  );
}

export default function TrackingPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let interval;
    const load = async () => {
      try {
        const res = await publicAPI.getTracking(token);
        setData(res.data);
        setError(null);
      } catch (e) {
        setError(e.response?.data?.detail || "Tracking link not found or expired.");
      } finally {
        setLoading(false);
      }
    };
    load();
    // Refresh every 60 seconds while en-route
    interval = setInterval(load, 60_000);
    return () => clearInterval(interval);
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="text-center">
          <div className="text-4xl mb-3">🔍</div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">Link not found</h2>
          <p className="text-gray-500">{error}</p>
        </div>
      </div>
    );
  }

  const company = data?.company || {};
  const tech = data?.technician;
  const etaTime = formatTime(data?.estimated_arrival);
  const arrivedTime = formatTime(data?.actual_arrival);
  const minutesLeft = data?.minutes_remaining;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm px-4 py-4 flex items-center gap-3">
        {company.logo_url ? (
          <img src={company.logo_url} alt={company.name} className="h-10 w-auto object-contain" />
        ) : (
          <div className="h-10 w-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-lg">
            {(company.name || "F").charAt(0)}
          </div>
        )}
        <div>
          <p className="font-semibold text-gray-900">{company.name || "Your Service Company"}</p>
          {company.phone && (
            <a href={`tel:${company.phone}`} className="text-sm text-blue-600">
              {company.phone}
            </a>
          )}
        </div>
      </header>

      <main className="flex-1 max-w-lg mx-auto w-full px-4 py-6 space-y-4">
        {/* Greeting */}
        <div className="text-center py-2">
          <p className="text-gray-600 text-lg">
            Hi {data.customer_first_name || "there"}!
          </p>
          <div className="mt-2">
            <StatusBadge status={data.status} />
          </div>
        </div>

        {/* ETA Card */}
        {data.status === "EN_ROUTE" && (
          <div className="bg-white rounded-2xl shadow p-5 text-center">
            <div className="text-5xl mb-2">🚗</div>
            <h2 className="text-xl font-semibold text-gray-900">On the way!</h2>
            {etaTime && (
              <p className="text-gray-600 mt-1">
                Estimated arrival: <strong>{etaTime}</strong>
                {minutesLeft != null && minutesLeft > 0 && (
                  <span className="text-gray-400 ml-1">(~{minutesLeft} min)</span>
                )}
                {minutesLeft === 0 && (
                  <span className="text-green-600 ml-1">(arriving now)</span>
                )}
              </p>
            )}
          </div>
        )}

        {data.status === "IN_PROGRESS" && (
          <div className="bg-white rounded-2xl shadow p-5 text-center">
            <div className="text-5xl mb-2">🏠</div>
            <h2 className="text-xl font-semibold text-gray-900">Technician has arrived</h2>
            {arrivedTime && (
              <p className="text-gray-500 mt-1">Arrived at {arrivedTime}</p>
            )}
          </div>
        )}

        {data.status === "COMPLETED" && (
          <div className="bg-white rounded-2xl shadow p-5 text-center">
            <div className="text-5xl mb-2">✅</div>
            <h2 className="text-xl font-semibold text-gray-900">Service complete!</h2>
            <p className="text-gray-500 mt-1">Thank you for choosing {company.name || "us"}.</p>
          </div>
        )}

        {/* Technician Card */}
        {tech && (
          <div className="bg-white rounded-2xl shadow p-5 flex items-center gap-4">
            {tech.photo_url ? (
              <img src={tech.photo_url} alt={tech.name} className="h-14 w-14 rounded-full object-cover" />
            ) : (
              <div className="h-14 w-14 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-xl">
                {(tech.name || "T").charAt(0)}
              </div>
            )}
            <div>
              <p className="font-semibold text-gray-900">{tech.name}</p>
              <p className="text-sm text-gray-500">Service Technician</p>
              {tech.vehicle_info && (
                <p className="text-sm text-gray-400 mt-0.5">{tech.vehicle_info}</p>
              )}
            </div>
          </div>
        )}

        {/* Service Details */}
        <div className="bg-white rounded-2xl shadow p-5 space-y-2">
          <h3 className="font-semibold text-gray-700 text-sm uppercase tracking-wide">Service Details</h3>
          {data.job_type && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Service</span>
              <span className="text-gray-900 font-medium capitalize">{data.job_type.replace(/_/g, " ")}</span>
            </div>
          )}
          {data.property_address && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Address</span>
              <span className="text-gray-900 font-medium text-right max-w-[60%]">{data.property_address}</span>
            </div>
          )}
          {(data.service_window_start || data.service_window_end) && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Window</span>
              <span className="text-gray-900 font-medium">
                {formatTime(data.service_window_start)} – {formatTime(data.service_window_end)}
              </span>
            </div>
          )}
        </div>

        {/* Contact */}
        {company.phone && (
          <div className="text-center">
            <p className="text-sm text-gray-500">Questions?</p>
            <a
              href={`tel:${company.phone}`}
              className="mt-1 inline-flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-full font-medium text-sm hover:bg-blue-700 transition-colors"
            >
              📞 Call {company.name}
            </a>
          </div>
        )}
      </main>

      <footer className="text-center text-xs text-gray-400 py-4">
        Powered by FieldOS
      </footer>
    </div>
  );
}
