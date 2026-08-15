/* Optional geographic context. This map records a project location; it does
 * not claim to infer storage suitability from terrain or satellite imagery. */
(() => {
  const API = location.hostname.endsWith("github.io") ? "https://hyleakai-152424867743.asia-south1.run.app" : "";
  const form = document.querySelector("#site-form");
  if (!form) return;
  const style = document.createElement("style");
  style.textContent = `#site-map-card{margin-top:13px;padding-top:13px;border-top:1px solid #27403a}#site-map{height:255px;border:1px solid #27403a;margin-top:8px}.map-toolbar{display:flex;gap:7px}.map-toolbar input{flex:1;min-width:0;background:#091512;color:#e8f0ec;border:1px solid #27403a;padding:8px;font:12px ui-monospace,monospace}.map-toolbar button{padding:8px 10px;font-size:11px}.map-context-note{margin:7px 0 0;color:#9daca5;font:10px/1.5 ui-monospace,monospace}`;
  document.head.append(style);
  form.insertAdjacentHTML("afterend", `<div id="site-map-card"><div class="eyebrow">Geographic context / optional</div><div class="map-toolbar"><input id="site-search" placeholder="Find a city, basin, or coordinates"><button type="button" id="site-find">Find</button></div><div id="site-map"></div><p class="map-context-note" id="site-map-note">Terrain context only. Click the map to set project latitude/longitude; geological suitability still requires subsurface data.</p></div>`);
  const note = document.querySelector("#site-map-note");
  function setLocation(lat, lng, marker, map) {
    form.elements.latitude.value = Number(lat).toFixed(5); form.elements.longitude.value = Number(lng).toFixed(5);
    marker.setPosition({lat:Number(lat), lng:Number(lng)}); map.panTo({lat:Number(lat), lng:Number(lng)});
    note.textContent = `Project coordinates set: ${Number(lat).toFixed(5)}, ${Number(lng).toFixed(5)}. This is geographic context only.`;
  }
  async function start() {
    try {
      const config = await (await fetch(`${API}/v1/public-config`)).json();
      if (!config.maps_enabled) { note.textContent = "Map is not configured on this deployment."; return; }
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(config.google_maps_browser_api_key)}&v=weekly`;
      script.async = true; script.onload = () => {
        const map = new google.maps.Map(document.querySelector("#site-map"), {center:{lat:20.5937,lng:78.9629},zoom:4,mapTypeId:"terrain",streetViewControl:false,mapTypeControl:true});
        const marker = new google.maps.Marker({map}); const geocoder = new google.maps.Geocoder();
        map.addListener("click", e => setLocation(e.latLng.lat(), e.latLng.lng(), marker, map));
        document.querySelector("#site-find").onclick = () => geocoder.geocode({address:document.querySelector("#site-search").value}, (results,status) => { if(status === "OK" && results[0]) { const loc=results[0].geometry.location; map.fitBounds(results[0].geometry.viewport); setLocation(loc.lat(),loc.lng(),marker,map); } else note.textContent=`Location search failed: ${status}. You can still click the map.`; });
      };
      script.onerror = () => { note.textContent = "Google Maps could not load. Check the API key's HTTP-referrer and API restrictions."; };
      document.head.append(script);
    } catch (_) { note.textContent = "Map configuration is unavailable."; }
  }
  start();
})();
