import { Link } from "react-router-dom";

function Sidebar() {
  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen">

      <div className="text-2xl font-bold p-6 border-b border-gray-700">
        📸 PicDrop AI
      </div>

      <nav className="flex flex-col p-4 gap-2">

        <Link className="hover:bg-gray-700 rounded p-3" to="/">
          📊 Dashboard
        </Link>

        <Link className="hover:bg-gray-700 rounded p-3" to="/events">
          📅 Events
        </Link>

        <Link className="hover:bg-gray-700 rounded p-3" to="/gallery">
          🖼 Gallery
        </Link>

        <Link className="hover:bg-gray-700 rounded p-3" to="/clients">
          👥 Clients
        </Link>

        <Link className="hover:bg-gray-700 rounded p-3" to="/brand">
          🎨 Brand Settings
        </Link>

      </nav>

    </aside>
  );
}

export default Sidebar;