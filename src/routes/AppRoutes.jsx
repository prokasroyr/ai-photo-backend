import { BrowserRouter, Routes, Route } from "react-router-dom";

import DashboardLayout from "../layouts/DashboardLayout";

import Dashboard from "../pages/dashboard/Dashboard";
import CreateEvent from "../pages/events/CreateEvent";
import MyEvents from "../pages/events/MyEvents";
import EventDetails from "../pages/events/EventDetails";


function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/events" element={<MyEvents />} />
          <Route path="/events/create" element={<CreateEvent />} />

          {/* পুরনো ও নতুন দুই URL-ই কাজ করবে */}
          <Route path="/event/:id" element={<EventDetails />} />
          <Route path="/events/:id" element={<EventDetails />} />

          
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default AppRoutes;