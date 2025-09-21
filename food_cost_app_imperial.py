# Create message
            msg = MimeMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Subject'] = subject
            
            msg.attach(MimeText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            text = msg.as_string()
            server.sendmail(self.sender_email, self.recipient_email, text)
            server.quit()
            
            return True
            
        except Exception as e:
            st.error(f"Email notification failed: {str(e)}")
            return False
    
    def _parse_amount_unit(self, input_str):
        match = re.match(r'(\d+(?:\.\d+)?)\s*(.*)', input_str.strip().lower())
        if match:
            amount = float(match.group(1))
            unit = match.group(2).strip()
            if unit in self.unit_conversions:
                return amount, unit
        raise ValueError(f"Invalid format. Use: '2.5 lbs', '1 cup', '16 oz'")
    
    def add_inventory(self):
        st.subheader("📦 Add Inventory Item")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            item = st.text_input("Item Name", placeholder="Ground Beef", key="inventory_item")
        with col2:
            quantity_input = st.text_input("Quantity & Unit", placeholder="5 lbs", key="inventory_qty")
        with col3:
            cost_input = st.number_input("Cost per Unit ($)", min_value=0.0, step=0.01, format="%.2f", key="inventory_cost")
        
        if st.button("➕ Add to Inventory", type="primary", key="add_inventory"):
            try:
                if item and quantity_input:
                    quantity, unit = self._parse_amount_unit(quantity_input)
                    cost = cost_input
                    
                    # Check if exists
                    existing = self.inventory[self.inventory['Item'] == item]
                    if not existing.empty:
                        idx = existing.index[0]
                        current_q = self.inventory.loc[idx, 'Quantity']
                        self.inventory.loc[idx, 'Quantity'] = current_q + quantity
                        st.warning(f"Updated existing {item} inventory")
                    else:
                        new_row = pd.DataFrame({
                            'Item': [item], 'Quantity': [quantity], 
                            'Unit': [unit], 'Cost_Per_Unit': [cost]
                        })
                        self.inventory = pd.concat([self.inventory, new_row], ignore_index=True)
                    
                    st.success(f"✅ Added: {quantity} {unit} of {item} at ${cost:.2f}/{unit}")
                    st.rerun()
                else:
                    st.error("Please fill all fields")
            except ValueError as e:
                st.error(str(e))
    
    def view_inventory(self):
        st.subheader("📋 Current Inventory")
        if self.inventory.empty:
            st.info("👆 Add some items above to get started!")
        else:
            st.dataframe(self.inventory, use_container_width=True, hide_index=True)
    
    def add_recipe(self):
        st.subheader("🍽️ Create Recipe & Calculate Costs")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            recipe_name = st.text_input("Recipe Name", placeholder="Classic Burger", key="recipe_name")
        with col2:
            selling_price = st.number_input("Selling Price ($)", min_value=0.0, step=0.01, format="%.2f", key="selling_price")
        
        # Dynamic ingredients input
        st.subheader("🥩 Add Ingredients")
        ingredients_container = st.container()
        ingredients_data = []
        
        with ingredients_container:
            # Create input fields dynamically
            num_ingredients = st.number_input("Number of ingredients:", min_value=1, max_value=10, value=3, key="num_ingredients")
            
            for i in range(num_ingredients):
                st.markdown(f"**Ingredient {i+1}:**")
                ingredient_col1, ingredient_col2, ingredient_col3 = st.columns([2, 2, 1])
                
                with ingredient_col1:
                    item_name = st.text_input(f"Item name", placeholder="Ground Beef", key=f"item_name_{i}")
                with ingredient_col2:
                    amount_input = st.text_input(f"Amount", placeholder="0.25 lbs", key=f"amount_{i}")
                with ingredient_col3:
                    st.empty()
                
                if item_name and amount_input:
                    ingredients_data.append({'item': item_name, 'amount': amount_input})
        
        if st.button("💰 Calculate Food Cost", type="primary", key="calc_cost"):
            try:
                if recipe_name and selling_price and ingredients_data:
                    total_cost = 0.0
                    cost_breakdown = []
                    
                    # Calculate costs
                    for ing in ingredients_data:
                        amount_str = ing['amount']
                        item_name = ing['item']
                        
                        # Parse amount
                        amount, unit = self._parse_amount_unit(amount_str)
                        
                        # Find cost from inventory
                        existing = self.inventory[self.inventory['Item'] == item_name]
                        if existing.empty:
                            st.warning(f"⚠️ No cost data for {item_name} - skipping")
                            continue
                        
                        unit_cost = existing.iloc[0]['Cost_Per_Unit']
                        inv_unit = existing.iloc[0]['Unit']
                        
                        # Calculate item cost
                        item_cost = amount * unit_cost
                        total_cost += item_cost
                        
                        cost_breakdown.append({
                            'Ingredient': item_name,
                            'Amount': f"{amount} {unit}",
                            'Cost': f"${item_cost:.2f}"
                        })
                        self.recipes[recipe_name] = {item_name: {'amount': amount, 'unit': unit}}
                    
                    # Display results
                    st.markdown("---")
                    st.subheader(f"💵 Food Cost Analysis: {recipe_name}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Cost", f"${total_cost:.2f}")
                    with col2:
                        food_cost_pct = (total_cost / selling_price) * 100
                      
                        status = "✅ Optimal (25-35%)" if 25 <= food_cost_pct <= 35 else "⚠️ Review Pricing"
                        st.metric("Food Cost %", f"{food_cost_pct:.1f}%", delta=status)
                    with col3:
                        margin = 100 - food_cost_pct
                        st.metric("Profit Margin", f"{margin:.1f}%")
                    
                    # Breakdown table
                    if cost_breakdown:
                        st.subheader("📊 Detailed Breakdown")
                        df_breakdown = pd.DataFrame(cost_breakdown)
                        st.dataframe(df_breakdown, use_container_width=True, hide_index=True)
                    
                    # Actionable insights
                    st.markdown("---")
                    st.subheader("🎯 Action Items")
                    if food_cost_pct > 35:
                        st.error(f"🔴 **High Cost Alert**: {food_cost_pct:.1f}% is above target. Consider:")
                        st.markdown("• Reducing portion sizes")
                        st.markdown("• Finding cheaper suppliers")
                        st.markdown("• Raising menu price")
                    elif food_cost_pct < 25:
                        st.success(f"🟢 **Excellent Margin**: {food_cost_pct:.1f}% - This is a winner!")
                    else:
                        st.info(f"✅ **Perfect Balance**: {food_cost_pct:.1f}% - Right in the sweet spot!")
                    
                    st.success(f"🎉 Analysis complete! Save this recipe for future tracking.")
                    
                else:
                    st.error("Please complete all recipe fields and add ingredients")
            except Exception as e:
                st.error(f"Error calculating costs: {str(e)}")
    
    def feedback_form(self):
        st.markdown("---")
        st.markdown("## 🎤 Your Feedback Helps Us Improve!")
        st.markdown("*Takes 30 seconds - your input shapes the tool restaurants actually use*")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("### ⭐ Quick Rating")
            overall_rating = st.slider("How valuable was this tool?", 1, 5, 3, key="overall_rating")
            ease_rating = st.slider("How easy was it to use?", 1, 5, 4, key="ease_rating")
            value_rating = st.slider("Would you pay $29/month for this?", 1, 5, 3, key="value_rating")
        
        with col2:
            st.markdown("### 💬 Tell Us More")
            restaurant_name = st.text_input("Your Restaurant Name", placeholder="Joe's Diner", key="restaurant_name")
            comments = st.text_area("What did you like? What could be better?", 
                                  placeholder="Example: 'Love the instant calculations! Would love to track waste too.'", 
                                  height=100, key="comments")
            email = st.text_input("Email (optional - for follow-up)", placeholder="joe@joesdiner.com", key="email")
            interested_paid = st.checkbox("Yes, I'd be interested in the paid version", key="interested_paid")
        
        if st.button("📤 Submit Feedback & Get Your Report", type="primary", key="submit_feedback"):
            if restaurant_name or comments or email:
                # Prepare feedback data
                feedback_data = {
                    'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'Restaurant_Name': restaurant_name,
                    'Overall_Rating': overall_rating,
                    'Ease_of_Use': ease_rating,
                    'Value_Rating': value_rating,
                    'Comments': comments,
                    'Email': email,
                    'Interested_Paid': interested_paid
                }
                
                # Save to CSV
                new_feedback = pd.DataFrame([feedback_data])
                self.feedback_df = pd.concat([self.feedback_df, new_feedback], ignore_index=True)
                self._save_feedback()
                
                # Send email notification
                email_sent = self.send_notification_email(feedback_data)
                
                # Success message
                st.balloons()
                if email_sent:
                    st.success("🎉 Thank you! Your feedback saved and team notified.")
                else:
                    st.success("🎉 Thank you! Your feedback saved.")
                
                st.markdown("### 📋 **Your Free Profit Report**")
                st.markdown("""
                **Based on your test:**
                - **Instant Savings**: 5-10% food cost reduction = $500-2000/month
                - **Time Saved**: 2-3 hours/week on manual calculations
                - **Features Coming**: Supplier price tracking, waste alerts, menu optimization
                
                **Ready for more?** I'll follow up with special pricing for early adopters.
                """)
                
                # Show summary stats
                if len(self.feedback_df) > 1:
                    avg_rating = self.feedback_df['Overall_Rating'].mean()
                    st.metric("Average User Rating", f"{avg_rating:.1f}/5")
                
                st.markdown("---")
                st.markdown("*Share this tool with your chef/manager: [Copy Link]*")
                
            else:
                st.warning("Please share your restaurant name or comments to submit!")
    
    def view_feedback_summary(self):
        """Admin view - only show if debug mode"""
        if st.sidebar.checkbox("👨‍💼 Admin: View Feedback", key="admin_view"):
            st.subheader("📊 Feedback Summary")
            if self.feedback_df.empty:
                st.info("No feedback collected yet")
            else:
                col1, col2, col3 = st.columns(3)
                with col1:
                    avg_rating = self.feedback_df['Overall_Rating'].mean()
                    st.metric("Avg Rating", f"{avg_rating:.1f}/5")
                with col2:
                    interested_count = self.feedback_df['Interested_Paid'].sum()
                    st.metric("Interested in Paid", f"{interested_count}/{len(self.feedback_df)}")
                with col3:
                    st.metric("Total Responses", f"{len(self.feedback_df)}")
                
                st.dataframe(self.feedback_df, use_container_width=True)
    
    def run(self):
        # Custom CSS for branding
        st.markdown("""
        <style>
        .main .block-container {
            padding-top: 1rem;
        }
        .stMetric > label {
            color: #1f77b4;
            font-size: 14px;
        }
        .stSuccess {
            background-color: #d4edda;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.title("🍔 Restaurant Food Cost & Inventory Calculator")
        st.markdown("### *Track costs • Save 5-10% on food expenses • Make better menu decisions*")
        
        # Sidebar
        st.sidebar.header("⚙️ Quick Start")
        st.sidebar.markdown("""
        **Target Goal:** Keep food costs at **25-35%** of menu price
        
        **💰 Pro Tip:** Items over 35%? Adjust portions or find new suppliers!
        """)
        
        use_inventory = st.sidebar.checkbox("📦 Enable Inventory Tracking", value=True, key="use_inventory")
        
        # Email setup notice (only show in development)
        if st.sidebar.checkbox("📧 Test Email Setup", key="email_setup"):
            st.sidebar.markdown("""
            **Email Configuration:**
            - Sender: your-app@gmail.com
            - Recipient: sam@5starstudios.com
            - Use Gmail App Password (not regular password)
            
            **Setup Steps:**
            1. Enable 2FA on your Gmail
            2. Generate App Password
            3. Add to Streamlit Secrets
            """)
        
        # Main tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📦 Inventory", "🍽️ Recipes", "📊 Dashboard", "🎤 Feedback"])
        
        with tab1:
            self.add_inventory()
            if use_inventory:
                self.view_inventory()
            else:
                st.info("💡 Enable inventory tracking in sidebar to track stock levels")
        
        with tab2:
            self.add_recipe()
        
        with tab3:
            st.subheader("📈 Profit Dashboard")
            st.markdown("""
            ### 🎯 **Key Metrics to Watch**
            | Metric | Target | Why It Matters |
            |--------|--------|----------------|
            | Food Cost % | 25-35% | Direct impact on profits |
            | Inventory Turnover | 7-10x/year | Fresh ingredients, less waste |
            | Menu Item Margin | 65-75% | Focus on high-profit items |
            
            ### 💡 **Quick Wins**
            1. **High-cost items (>35%)**: Reduce portions by 10-15%
            2. **Low-stock alerts**: Order in bulk for 10-20% savings
            3. **Menu engineering**: Promote your top 3 profit-makers
            """)
        
        with tab4:
            self.feedback_form()
        
        # Admin view (hidden unless enabled)
        self.view_feedback_summary()
        
        # Footer
        st.markdown("---")
        st.markdown("*Built for independent restaurants • Questions? Reply to the email you received*")

# Run the app
if __name__ == "__main__":
    app = RestaurantFoodCostApp()
    app.run()
