import React from 'react';
import { BrowserRouter as Router, Route, Switch } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import HomeComponent from './modules/home/home.component';
import SetupComponent from './modules/setup/setup.component';
import AnalysisComponent from './modules/analysis/analysis-component';
import './styles/theme.css';
import './app.component.css';

export const io = require('socket.io-client');
export const socket = io.connect('http://localhost:5007/', { transports: ['polling']})

socket.on('connect', function() {
    socket.send('message', 'User has connected!');
});

socket.on('connect_error', (err) => {
    console.log(`connect error due to ${err}`)
})

const AppComponent = () => {
    return (
        <Router>
            <div className="nano-app">
                <Header />
                <main className="nano-main">
                    <Switch>
                        <Route exact path="/" component={HomeComponent} />
                        <Route path="/setup" component={SetupComponent} />
                        <Route path="/analysis/:id?" component={AnalysisComponent} />
                    </Switch>
                </main>
                <Footer />
            </div>
        </Router>
    );
}

export default AppComponent;
